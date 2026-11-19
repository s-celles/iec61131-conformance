#!/usr/bin/env python3
"""Property monitors for the standard function blocks.

    python3 -I tools/monitor/monitor.py [--check]

Each property is a rule read off the text of IEC 61131-3 edition 2 (2003):
the function block bodies of tables 34 (SR, RS), 35 (R_TRIG, F_TRIG) and 36
(CTU, CTD, CTUD), and the timing diagrams of table 38 (TP, TON, TOF). They
are checked, cycle by cycle, against the expected .trace of each test that
drives one of these blocks, and against what every runtime recorded in
notes/evidence/. An expected trace that violates a property is an error in
the trace (the traces were written by an AI assistant, see
notes/trace-audit-2026-11-18.md); a runtime that violates one deviates from
that rule, whatever the trace says. --check exits 1 if a trace violates a
property.

The properties are deliberately partial: where the text leaves a value to
the implementer (the counters' PVmin and PVmax, NOTE under table 36) they
accept every permitted choice, here a counter that stops at PV or at the
bound of its type.
"""
import argparse
import pathlib
import re
from collections import namedtuple

Violation = namedtuple("Violation", "prop cycle message")

INT_MIN, INT_MAX = -32768, 32767

# test -> [(block, {pin: trace variable}, parameters)]
BINDINGS = {
    "edge/r_trig": [("R_TRIG", {"CLK": "clk", "Q": "q"}, {})],
    "edge/f_trig": [("F_TRIG", {"CLK": "clk", "Q": "q"}, {})],
    "edge/power_on_clk_true": [("R_TRIG", {"CLK": "clk", "Q": "qr"}, {}), ("F_TRIG", {"CLK": "clk", "Q": "qf"}, {})],
    "edge/sr_rs": [("SR", {"S1": "s", "R": "r", "Q1": "q_sr"}, {}), ("RS", {"S": "s", "R1": "r", "Q1": "q_rs"}, {})],
    "counters/ctu": [("CTU", {"CU": "cu", "R": "r", "Q": "q", "CV": "cv"}, {"PV": 3})],
    "counters/ctd": [("CTD", {"CD": "cd", "LD": "ld", "Q": "q", "CV": "cv"}, {"PV": 3})],
    "counters/ctud": [("CTUD", {"CU": "cu", "CD": "cd", "R": "r", "LD": "ld", "QU": "qu", "QD": "qd", "CV": "cv"}, {"PV": 2})],
    "counters/ctd_bounds": [("CTD", {"CD": "cd", "LD": "ld", "Q": "q", "CV": "cv"}, {"PV": -32768})],
    "counters/ctud_bounds": [("CTUD", {"CU": "cu", "CD": "cd", "R": "r", "LD": "ld", "QU": "qu", "QD": "qd", "CV": "cv"}, {"PV": 32767})],
    "timers/ton": [("TON", {"IN": "in", "Q": "q", "ET": "et"}, {"PT": 300})],
    "timers/tof": [("TOF", {"IN": "in", "Q": "q", "ET": "et"}, {"PT": 200})],
    "timers/tp": [("TP", {"IN": "in", "Q": "q", "ET": "et"}, {"PT": 300})],
}
RUNTIMES = ("ironplc", "matiec", "openplc", "strucpp", "rusty", "4diac", "rk", "trust")


# ------------------------------------------------------------------ records

def value(text):
    if text in ("TRUE", "FALSE"):
        return text == "TRUE"
    m = re.fullmatch(r"T#(-?\d+)ms", text)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"T#(-?\d+(?:\.\d+)?)s", text)
    if m:
        return round(float(m.group(1)) * 1000)
    try:
        return int(text)
    except ValueError:
        return text


def parse_records(text, inputs, outputs):
    """Per-cycle dicts from "N name=value ... => name=value ..." lines; an
    input not written on a line keeps its previous value."""
    current, out = {}, []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("#"):
            continue
        m = re.match(r"(\d+)\s+(.*?)=>\s*(.*)$", line)
        if not m:
            continue
        for side in (m.group(2), m.group(3)):
            for name, v in re.findall(r"([\w.]+)=(\S+)", side):
                current[name] = value(v)
        rec = dict(current)
        rec["_cycle"] = int(m.group(1))
        out.append(rec)
    return out


# --------------------------------------------------------------- properties

def check_block(block, rows, period, params):
    """Violations of the rules of `block` by rows of {pin: value}, one per
    cycle, `period` ms apart. An output may be None (a value the trace
    leaves open): it is not checked, and what depends on it is not either."""
    out = []

    def bad(prop, n, msg):
        out.append(Violation(prop, n, msg))

    def differs(obs, exp):
        return obs is not None and exp is not None and obs != exp

    prev = {"CLK": False, "CU": False, "CD": False, "IN": False, "Q": False, "Q1": False,
            "ET": 0, "CV": params.get("CV0", 0)}
    seen_in = False
    for n, r in enumerate(rows):
        if block == "R_TRIG":      # table 35: Q := CLK AND NOT M; M := CLK; M starts FALSE
            exp = r["CLK"] and not prev["CLK"]
            if differs(r["Q"], exp):
                bad("R_TRIG.Q", n, f"Q={r['Q']}, body gives {exp}")
        elif block == "F_TRIG":    # table 35: Q := NOT CLK AND NOT M; M := NOT CLK; M starts FALSE
            m = (not prev["CLK"]) if n else False
            exp = (not r["CLK"]) and not m
            if differs(r["Q"], exp):
                bad("F_TRIG.Q", n, f"Q={r['Q']}, body gives {exp}")
        elif block in ("SR", "RS"):  # table 34: SR Q1 := S1 OR (NOT R AND Q1); RS Q1 := NOT R1 AND (S OR Q1)
            s, rr = (r["S1"], r["R"]) if block == "SR" else (r["S"], r["R1"])
            if block == "SR":
                exp = True if s else (None if prev["Q1"] is None else (not rr and prev["Q1"]))
            else:
                exp = False if rr else (True if s else prev["Q1"])
            if differs(r["Q1"], exp):
                bad(f"{block}.Q1", n, f"Q1={r['Q1']}, body gives {exp}")
        elif block in ("CTU", "CTD", "CTUD"):
            out += counter(block, n, r, prev, params)
        elif block == "TON":       # table 38, on-delay
            pt = params["PT"]
            if not r["IN"] or not prev["IN"]:
                exp_et = 0
            else:
                exp_et = None if prev["ET"] is None else min(prev["ET"] + period, pt)
            if differs(r["ET"], exp_et):
                bad("TON.ET", n, f"ET={r['ET']}, diagram gives {exp_et}")
            exp_q = False if not r["IN"] else (None if r["ET"] is None else r["ET"] >= pt)
            if differs(r["Q"], exp_q):
                bad("TON.Q", n, f"Q={r['Q']} with IN={r['IN']}, ET={r['ET']}, PT={pt}")
        elif block == "TOF":       # table 38, off-delay
            pt = params["PT"]
            if r["IN"]:
                seen_in, exp_et, exp_q = True, 0, True
            else:
                if prev["IN"] or not seen_in:
                    exp_et = 0
                else:
                    exp_et = None if prev["ET"] is None else min(prev["ET"] + period, pt)
                exp_q = None if r["ET"] is None else (seen_in and r["ET"] < pt)
            if differs(r["ET"], exp_et):
                bad("TOF.ET", n, f"ET={r['ET']}, diagram gives {exp_et}")
            if differs(r["Q"], exp_q):
                bad("TOF.Q", n, f"Q={r['Q']} with IN={r['IN']}, ET={r['ET']}" + ("" if seen_in else ", IN never TRUE yet"))
        elif block == "TP":        # table 38, pulse
            pt = params["PT"]
            rising = r["IN"] and not prev["IN"]
            if prev["Q"] is None or r["Q"] is None:
                pass
            elif r["Q"] and not prev["Q"]:
                if not rising:
                    bad("TP.start", n, "a pulse starts without a rising edge of IN")
                if differs(r["ET"], 0):
                    bad("TP.ET", n, f"ET={r['ET']} at the start of a pulse")
            elif prev["Q"]:
                exp_et = None if prev["ET"] is None else min(prev["ET"] + period, pt)
                if exp_et == pt and not r["IN"] and r["ET"] == 0:
                    pass       # the diagram leaves ET open on the cycle a pulse ends with IN FALSE
                elif differs(r["ET"], exp_et):
                    bad("TP.ET", n, f"ET={r['ET']} during the pulse, diagram gives {exp_et}")
                et = exp_et if exp_et is not None else r["ET"]
                if et is not None and r["Q"] != (et < pt):
                    bad("TP.Q", n, f"Q={r['Q']} with ET={et}, PT={pt}")
            else:
                if rising and pt > 0:
                    bad("TP.start", n, "a rising edge of IN while idle starts no pulse")
                exp_et = prev["ET"] if r["IN"] else 0
                if differs(r["ET"], exp_et):
                    bad("TP.ET", n, f"ET={r['ET']} after the pulse, diagram gives {exp_et}")
        else:
            raise ValueError(block)
        prev.update({k: v for k, v in r.items() if k in prev})
    return out


def counter(block, n, r, prev, params):
    """Table 36 bodies. CU and CD are edge-triggered inputs; PVmin and PVmax
    are implementation-dependent, so a count may also stop at PV (0 for
    CTD) or at the bound of INT."""
    pv, out, cv, last = params["PV"], [], r["CV"], prev["CV"]
    if cv is None:
        return out
    up = r.get("CU", False) and not prev["CU"]
    down = r.get("CD", False) and not prev["CD"]

    def counts(exp, stop):
        return cv == exp or (cv == last and stop)

    ok, rule = True, "count"
    if block in ("CTU", "CTUD") and r.get("R"):
        ok, rule = cv == 0, "reset"
    elif block in ("CTD", "CTUD") and r.get("LD"):
        ok, rule = cv == pv, "load"
    elif last is None:
        ok = True
    elif block == "CTUD" and up and down:
        ok = cv == last
    elif up and block != "CTD":
        ok = counts(last + 1, last >= pv or last >= INT_MAX)
    elif down and block != "CTU":
        ok = counts(last - 1, last <= 0 or last <= INT_MIN)
    else:
        ok = cv == last
    if not ok:
        out.append(Violation(f"{block}.{rule}", n, f"CV={cv} after CV={last}"))
    q = {"CTU": [("Q", cv >= pv)], "CTD": [("Q", cv <= 0)], "CTUD": [("QU", cv >= pv), ("QD", cv <= 0)]}[block]
    for pin, exp in q:
        if r[pin] is not None and r[pin] != exp:
            out.append(Violation(f"{block}.Q", n, f"{pin}={r[pin]} with CV={cv}, PV={pv}"))
    return out


# --------------------------------------------------------------- repository

def evidence_block(text, test):
    m = re.search(r"(?ms)^### conformance/" + re.escape(test) + r"\.st\n(.*?)(?=^### |^\d+ tests: |\Z)", text)
    return m.group(1) if m else ""


def check_records(test, recs, period):
    """A "?" value (left open by the trace) is passed on as None."""
    out = []
    for block, pins, params in BINDINGS[test]:
        if not recs or any(v not in recs[0] for v in pins.values()):
            continue
        rows = [{pin: (None if rec[var] == "?" else rec[var]) for pin, var in pins.items()} for rec in recs]
        out += check_block(block, rows, period, params)
    return out


def run(root):
    """[(test, source, violations)], source "trace" or a runtime with records."""
    root, report = pathlib.Path(root), []
    evidence = {rt: (root / f"notes/evidence/{rt}-run.txt").read_text() for rt in RUNTIMES}
    for test in BINDINGS:
        trace = (root / f"conformance/{test}.trace").read_text()
        head, body = trace.split("\n---", 1)
        period = int(re.search(r"(?m)^period_ms:\s*(\d+)", head).group(1))
        inputs = re.search(r"(?m)^inputs:(.*)$", head).group(1).split()
        outputs = re.search(r"(?m)^outputs:(.*)$", head).group(1).split()
        report.append((test, "trace", check_records(test, parse_records(body, inputs, outputs), period)))
        for rt in RUNTIMES:
            recs = parse_records(evidence_block(evidence[rt], test), inputs, outputs)
            if recs:
                report.append((test, rt, check_records(test, recs, period)))
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=str(pathlib.Path(__file__).resolve().parents[2]))
    ap.add_argument("--check", action="store_true", help="exit 1 if an expected trace violates a property")
    a = ap.parse_args()
    report = run(a.root)
    bad_traces = 0
    for test, src, vs in report:
        if not vs:
            continue
        bad_traces += src == "trace"
        first = vs[0]
        print(f"{test:24} {src:8} {len(vs):3} violation(s), first: {first.prop} at cycle {first.cycle} ({first.message})")
    checked = sorted({(t, s) for t, s, _ in report})
    print(f"{len(BINDINGS)} tests, {len(checked)} (test, source) pairs checked; {bad_traces} expected trace(s) violate a property")
    if a.check and bad_traces:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
