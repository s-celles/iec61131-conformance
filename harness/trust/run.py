#!/usr/bin/env python3
"""Runs the conformance traces against truST (github.com/johannesPettersson80/trust-platform).

truST compiles Structured Text to native code. Its conformance driver, the example
`conformance_driver` of its trust-runtime crate, takes one test: it compiles the .st
with truST's test harness and starts it with its declared initial values, prints the
declared types of the outputs (`types name=TYPE ...`), and then, for each record read
on its standard input, writes the inputs, runs exactly one scan at PLC time
cycle * period_ms, and prints the outputs in .trace record syntax (a STRING as
#<hex bytes>), or `trap: <fault>` when the scan faults, which ends the run. A
CONFIGURATION in the .st (SPEC.md version 2) runs with its own tasks; a trace names
its variables as truST's harness resolves them. This script writes the records,
reads what the driver printed and compares it with the shared tracefmt rules.

Usage:
  run.py --driver PATH [--toolchain DIR] [--record] DIR_OR_FILE...

--toolchain is truST's native toolchain folder (built by its
scripts/native/build_toolchain_libraries.sh); without it the driver takes
TRUST_TOOLCHAIN from the environment, else the installed truST bundle.

Before the tests, a one-line program checks that the driver and the toolchain
work, so that a broken setup is not reported as a compile failure of every test
(the driver exits 1 for any build error, its toolchain's included).

Exit status: 0 when no test is FAIL or ERROR, 1 otherwise; 2 when the setup
check fails, before any test runs.
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "matiec"))
from tracefmt import Status, canonical_actual, parse_trace  # noqa: E402


SMOKE = "PROGRAM main\n  VAR_OUTPUT x : INT; END_VAR\n  x := 1;\nEND_PROGRAM\n"


def driver_env(opts):
    env = dict(os.environ)
    if opts.toolchain:
        env["TRUST_TOOLCHAIN"] = opts.toolchain
    return env


def setup_problem(opts):
    """None if the driver compiles and runs a one-line program, else why not."""
    with tempfile.TemporaryDirectory(prefix="trust-smoke-") as d:
        st = Path(d) / "smoke.st"
        st.write_text(SMOKE)
        try:
            r = subprocess.run([opts.driver, str(st), "100", "x"], input="0 \n", capture_output=True,
                               text=True, env=driver_env(opts), timeout=300)
        except OSError as e:
            return f"cannot start the driver: {e}"
    if r.returncode != 0 or "0 => x=1" not in r.stdout:
        return f"the driver fails on a one-line program (exit {r.returncode}): {(r.stderr or r.stdout).strip()[:2000]}"
    return None


def is_trap(rhs):
    return rhs == "trap" or rhs.startswith("trap:")


def run_test(st_path: Path, opts):
    trace = parse_trace(st_path.with_suffix(".trace").read_text())
    stdin = "".join(
        f"{rec.cycle} " + " ".join(f"{n}={v}" for n, v in rec.inputs) + "\n" for rec in trace.records
    )
    r = subprocess.run([opts.driver, str(st_path), str(trace.period_ms), *trace.outputs],
                       input=stdin, capture_output=True, text=True, env=driver_env(opts), timeout=300)
    if r.returncode == 1:
        verdict = "FAIL" if trace.status == Status.CONFORMANT else "DIFFERS"
        return verdict, ["truST failed to compile the program:\n" + r.stderr.rstrip()], []
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    if not lines or not lines[0].startswith("types"):
        return "ERROR", [f"the driver stopped (exit {r.returncode}): {r.stderr.strip()}"], []
    types = dict(tok.split("=", 1) for tok in lines[0].split()[1:])
    actual_by_cycle = {int(l.split()[0]): l for l in lines[1:]}

    problems = []
    recorded = []
    trapped = False
    for rec in trace.records:
        got = actual_by_cycle.get(rec.cycle)
        inp = "".join(f" {n}={v}" for n, v in rec.inputs)
        if got is None:
            problems.append(f"cycle {rec.cycle}: no output")
            break
        rhs = got.split("=>", 1)[1].strip()
        if is_trap(rhs):
            # record syntax: `trap`, the fault as a comment (as harness/rusty does)
            fault = rhs[5:].strip()
            recorded.append(f"{rec.cycle}{inp} => trap" + (f"   # {fault}" if fault else ""))
            trapped = True
            if rec.expected != "trap":
                problems.append(f"cycle {rec.cycle} (trace line {rec.line}): unexpected trap ({rhs})")
            break
        recorded.append(f"{rec.cycle}{inp} => {canonical_actual(rhs, types)}")
        if rec.expected == "trap":
            problems.append(f"cycle {rec.cycle} (trace line {rec.line}): expected a trap, got {rhs}")
            continue
        actual = dict(tok.split("=", 1) for tok in rhs.split())
        for name, value in rec.expected:
            if value.kind == "any":
                continue
            if not value.matches(actual.get(name), types[name]):
                shown = canonical_actual(f"{name}={actual.get(name)}", types).split("=", 1)[1]
                problems.append(f"cycle {rec.cycle} (trace line {rec.line}): {name} expected {value}, got {shown}")
    if r.returncode not in (0, 1) and not trapped:
        # the driver refused part way (exit 2): keep the cycles it printed
        last = max(actual_by_cycle) if actual_by_cycle else None
        where = f"after cycle {last}" if last is not None else "before the first cycle"
        return "ERROR", problems + [f"the driver stopped {where} (exit {r.returncode}): {r.stderr.strip()}"], recorded
    if trace.status == Status.CONFORMANT:
        return ("PASS" if not problems else "FAIL"), problems, recorded
    return ("SAME" if not problems else "DIFFERS"), problems, recorded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--driver", required=True, help="truST's conformance_driver executable")
    ap.add_argument("--toolchain", help="truST's native toolchain folder (TRUST_TOOLCHAIN)")
    ap.add_argument("--record", action="store_true")
    ap.add_argument("paths", nargs="+")
    opts = ap.parse_args()
    problem = setup_problem(opts)
    if problem:
        print(f"truST setup check failed, no test run: {problem}", file=sys.stderr)
        sys.exit(2)

    tests = []
    for p in opts.paths:
        p = Path(p)
        tests += sorted(p.rglob("*.st")) if p.is_dir() else [p]
    counts = {"PASS": 0, "FAIL": 0, "SAME": 0, "DIFFERS": 0, "ERROR": 0}
    for st in tests:
        try:
            verdict, problems, recorded = run_test(st, opts)
        except Exception as e:  # harness error
            verdict, problems, recorded = "ERROR", [repr(e)], []
        counts[verdict] += 1
        if opts.record:
            print(f"### {st}")
            for l in recorded:
                print(l)
        print(f"{verdict:8}{st}")
        for l in problems:
            print(f"        {l}")
    print()
    print(f"{len(tests)} tests: " + ", ".join(f"{v} {k.lower()}" for k, v in counts.items()))
    sys.exit(1 if counts["FAIL"] or counts["ERROR"] else 0)


if __name__ == "__main__":
    main()
