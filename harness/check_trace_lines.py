#!/usr/bin/env python3
"""Check that every "cycle N (trace line L)" in notes/evidence/*-run.txt
points at the record of cycle N in the test's .trace.

Editing a trace's comments can shift its lines after the evidence was
recorded; the runtime jobs of CI would then fail on line numbers alone.
This check needs no runtime. Run with python3 -I harness/check_trace_lines.py.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def stale(root=ROOT):
    out = []
    for f in sorted((root / "notes/evidence").glob("*-run.txt")):
        text = f.read_text()
        for m in re.finditer(r"(?ms)^### (conformance/\S+)\.st\n(.*?)(?=^### |\Z)", text):
            trace = root / (m.group(1) + ".trace")
            if not trace.exists():
                continue
            lines = trace.read_text().split("\n")
            for cycle, ln in re.findall(r"cycle (\d+) \(trace line (\d+)\)", m.group(2)):
                line = lines[int(ln) - 1] if int(ln) <= len(lines) else ""
                if not re.match(rf"\s*{cycle}\s", line):
                    out.append(f"{f.name}: {m.group(1)}: cycle {cycle} cites trace line {ln}: {line.strip()[:50]!r}")
    return out


if __name__ == "__main__":
    bad = stale()
    print("\n".join(bad) or "evidence trace-line references are consistent")
    sys.exit(1 if bad else 0)
