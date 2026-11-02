#!/usr/bin/env python3
"""Regenerate the results table of notes/comparison.md from notes/evidence.

The evidence files are the authority: each `notes/evidence/<runtime>-run.txt`
is the harness output at the pinned runtime commit (CI diffs it). The table
in `notes/comparison.md` between the `<!-- results:begin -->` and
`<!-- results:end -->` markers is derived from them by this script:

- one row per test, in the order of the current table (new tests are
  appended, grouped by directory);
- a cell is `PASS`/`SAME` as recorded, or `**FAIL**`/`**DIFFERS**`/`**ERROR**`
  with, in parentheses, the mismatching cycles (`cycle 4`, `cycles 5, 10-18`)
  or the stage that failed (`compile`, `build`, `configuration`, ...);
- the `note` column is hand-written and kept by test name;
- the `Totals:` line counts, per runtime, the `status: conformant` traces
  that pass, and the tests whose result is the same on every runtime.

Usage: python3 -I harness/summarize.py [--check]

With --check, exits 1 if notes/comparison.md is out of date (CI).
"""

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "notes" / "evidence"
COMPARISON = ROOT / "notes" / "comparison.md"
CONFORMANCE = ROOT / "conformance"

# (column title, evidence file stem), in table order
RUNTIMES = [
    ("IronPLC", "ironplc"),
    ("matiec", "matiec"),
    ("OpenPLC's matiec", "openplc"),
    ("STruC++", "strucpp"),
    ("RuSTy", "rusty"),
    ("4diac", "4diac"),
    ("rk", "rk"),
]

BEGIN = "<!-- results:begin -->"
END = "<!-- results:end -->"
STATUS_RE = re.compile(r"^(PASS|FAIL|SAME|DIFFERS|ERROR)\s+conformance/(\S+)\.st")
CYCLE_RE = re.compile(r"^\s+cycle (\d+) \(trace line \d+\):")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def read_evidence(stem):
    """Map test name -> (status, detail lines) from one evidence file."""
    results = {}
    current = None
    for raw in (EVIDENCE / f"{stem}-run.txt").read_text().splitlines():
        line = ANSI_RE.sub("", raw)
        m = STATUS_RE.match(line)
        if m:
            current = (m.group(1), [])
            results[m.group(2)] = current
            continue
        if line.startswith("### ") or re.match(r"^\d+ tests:", line) or line.startswith("exit "):
            current = None
            continue
        if current is not None and line.strip():
            current[1].append(line)
    return results


def compress(cycles):
    """[5, 10, 11, 12] -> 'cycles 5, 10-12'."""
    cycles = sorted(set(cycles))
    runs, start, prev = [], cycles[0], cycles[0]
    for c in cycles[1:]:
        if c == prev + 1:
            prev = c
            continue
        runs.append((start, prev))
        start = prev = c
    runs.append((start, prev))
    text = ", ".join(f"{a}" if a == b else f"{a}-{b}" for a, b in runs)
    return ("cycle " if len(cycles) == 1 else "cycles ") + text


def stage(detail):
    """Why a test could not be compared, from the harness's first lines."""
    head = " ".join(detail[:3]).lower()
    if "failed to compile" in head:
        return "compile"
    if "gcc failed" in head or "g++ failed" in head or "build" in head:
        return "build"
    if "is single" in head:
        return "SINGLE not driven"
    if "configuration" in head:
        return "configuration"
    return "see evidence"


def cell(status, detail):
    if status in ("PASS", "SAME"):
        return status
    cycles = [int(m.group(1)) for line in detail if (m := CYCLE_RE.match(line))]
    why = compress(cycles) if cycles else stage(detail)
    return f"**{status}** ({why})"


def trace_status(test):
    text = (CONFORMANCE / f"{test}.trace").read_text()
    m = re.search(r"^status:\s*(\S+)", text, re.M)
    return m.group(1) if m else "conformant"


def current_table(text):
    """Existing rows between the markers: ordered test names and their notes."""
    order, notes = [], {}
    inside = False
    for line in text.splitlines():
        if line.strip() == BEGIN:
            inside = True
            continue
        if line.strip() == END:
            break
        if inside and line.startswith("| ") and not line.startswith("| test ") and not line.startswith("|---"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            order.append(cells[0])
            notes[cells[0]] = cells[-1] if len(cells) > 1 else ""
    return order, notes


def build(text):
    evidence = {stem: read_evidence(stem) for _, stem in RUNTIMES}
    tests = set()
    for res in evidence.values():
        tests |= set(res)
    order, notes = current_table(text)
    rows = [t for t in order if t in tests]
    rows += sorted(t for t in tests if t not in order)

    lines = [BEGIN, "", "| test | " + " | ".join(name for name, _ in RUNTIMES) + " | note |",
             "|---" * (len(RUNTIMES) + 2) + "|"]
    passes = {stem: 0 for _, stem in RUNTIMES}
    agree = 0
    for t in rows:
        cells = []
        statuses = set()
        for _, stem in RUNTIMES:
            status, detail = evidence[stem].get(t, ("ERROR", ["not run"]))
            statuses.add(status)
            if status == "PASS":
                passes[stem] += 1
            cells.append(cell(status, detail))
        if len(statuses) == 1:
            agree += 1
        lines.append(f"| {t} | " + " | ".join(cells) + f" | {notes.get(t, '')} |")
    conformant = sum(1 for t in rows if trace_status(t) == "conformant")
    totals = "; ".join(f"{name} {passes[stem]}/{conformant}" for name, stem in RUNTIMES)
    lines += ["",
              f"Totals ({len(rows)} tests, {conformant} with `status: conformant`): "
              f"conformant tests passed, {totals}. "
              f"{agree} of the {len(rows)} tests have the same result on all seven runtimes.",
              "", END]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if comparison.md is out of date")
    args = ap.parse_args()
    text = COMPARISON.read_text()
    begin, end = text.find(BEGIN), text.find(END)
    if begin < 0 or end < 0:
        sys.exit(f"{COMPARISON}: markers {BEGIN} / {END} not found")
    new = text[:begin] + build(text) + text[end + len(END):]
    if new == text:
        print("notes/comparison.md is up to date")
        return
    if args.check:
        sys.exit("notes/comparison.md is out of date: run python3 -I harness/summarize.py")
    COMPARISON.write_text(new)
    print("notes/comparison.md updated")


if __name__ == "__main__":
    main()
