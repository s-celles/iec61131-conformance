#!/usr/bin/env python3
"""Differential run of generated programs on the locally built runtimes.

    python3 -I tools/fuzz/run.py --seeds 1-50 --out DIR \
        --ironplc-harness harness/ironplc/target/release/iec61131-conformance-ironplc \
        --ironplcc scratch/ironplc/compiler/target/release/ironplcc \
        --iec2c scratch/matiec/iec2c --matiec-lib scratch/matiec/lib \
        --openplc-iec2c scratch/openplc/utils/matiec_src/iec2c \
        --openplc-lib scratch/openplc/utils/matiec_src/lib \
        --strucpp "node scratch/strucpp/dist/node/cli.js" \
        --runtime-include scratch/strucpp/src/runtime/include

For each seed, gen.py writes DIR/fuzz_<seed>.st/.trace; every runtime whose
options are given is run through its harness on that file; a runtime that
does not PASS is a divergence from the reference evaluator (which only
transcribes the standard's tables, see gen.py), printed with the harness's
detail lines. Divergent programs stay in DIR for reduction by hand; the
reduced case then becomes a conformance/ test with a hand derivation.
Nothing here is run by CI.
"""

import argparse
import pathlib
import re
import shlex
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools" / "fuzz"))
import gen  # noqa: E402

VERDICT = re.compile(r"^(PASS|FAIL|SAME|DIFFERS|ERROR)\s")


def runtimes(a):
    """Name -> command prefix (the .st path is appended)."""
    rts = {}
    if a.ironplc_harness and a.ironplcc:
        rts["ironplc"] = [a.ironplc_harness, "--ironplcc", a.ironplcc]
    if a.iec2c and a.matiec_lib:
        rts["matiec"] = ["python3", "-I", str(ROOT / "harness/matiec/run.py"), "--iec2c", a.iec2c, "--matiec-lib", a.matiec_lib]
    if a.openplc_iec2c and a.openplc_lib:
        rts["openplc"] = ["python3", "-I", str(ROOT / "harness/matiec/run.py"), "--iec2c", a.openplc_iec2c, "--matiec-lib", a.openplc_lib]
    if a.strucpp and a.runtime_include:
        rts["strucpp"] = ["python3", "-I", str(ROOT / "harness/strucpp/run.py"), "--strucpp", a.strucpp, "--runtime-include", a.runtime_include]
    if a.plc and a.rusty_src:
        rts["rusty"] = ["python3", "-I", str(ROOT / "harness/rusty/run.py"), "--plc", a.plc, "--rusty-src", a.rusty_src]
    return rts


def run_one(cmd, st):
    p = subprocess.run(cmd + [str(st)], capture_output=True, text=True, cwd=ROOT)
    out = p.stdout + p.stderr
    verdict, detail = "ERROR", []
    for line in out.splitlines():
        m = VERDICT.match(line)
        if m:
            verdict = m.group(1)
        elif verdict != "ERROR" or line.strip():
            detail.append(line)
    return verdict, [d for d in detail if not re.match(r"^\d+ tests:", d)][:12]


def seeds_of(spec):
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += range(int(a), int(b) + 1)
        else:
            out.append(int(part))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="1-20", help="e.g. 1-50 or 3,7,9")
    ap.add_argument("--cycles", type=int, default=5)
    ap.add_argument("--stmts", type=int, default=6)
    ap.add_argument("--exclude", default="", help="features to leave out, see gen.EXCLUDABLE (known upstream issues)")
    ap.add_argument("--profile", choices=sorted(gen.PROFILES), default="core", help="type profile, see gen.PROFILES")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ironplc-harness")
    ap.add_argument("--ironplcc")
    ap.add_argument("--iec2c")
    ap.add_argument("--matiec-lib")
    ap.add_argument("--openplc-iec2c")
    ap.add_argument("--openplc-lib")
    ap.add_argument("--strucpp")
    ap.add_argument("--runtime-include")
    ap.add_argument("--plc")
    ap.add_argument("--rusty-src")
    a = ap.parse_args()
    rts = runtimes(a)
    if not rts:
        raise SystemExit("no runtime given")
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    counts = {n: {"PASS": 0, "other": 0} for n in rts}
    skipped = 0
    divergent = []
    for seed in seeds_of(a.seeds):
        r = gen.make(seed, a.cycles, a.stmts, excl=[x for x in a.exclude.split(",") if x], profile=a.profile)
        if r is None:
            skipped += 1
            continue
        st = out / f"fuzz_{seed}.st"
        st.write_text(r[0])
        (out / f"fuzz_{seed}.trace").write_text(r[1])
        bad = {}
        for name, cmd in rts.items():
            verdict, detail = run_one(cmd, st)
            if verdict == "PASS":
                counts[name]["PASS"] += 1
            else:
                counts[name]["other"] += 1
                bad[name] = (verdict, detail)
        if bad:
            divergent.append(seed)
            print(f"seed {seed}: {st}")
            for name, (verdict, detail) in bad.items():
                print(f"  {name}: {verdict}")
                for d in detail[:6]:
                    print(f"      {d[:140]}")
        else:
            st.unlink()
            (out / f"fuzz_{seed}.trace").unlink()
    print()
    for name, c in counts.items():
        print(f"{name:8s} {c['PASS']} pass, {c['other']} divergent")
    print(f"{skipped} seed(s) without a well-defined program; divergent seeds: {divergent or 'none'}")
    return 1 if divergent else 0


if __name__ == "__main__":
    sys.exit(main())
