#!/usr/bin/env python3
"""Runs the conformance traces against RuSTy (PLC-lang/rusty, `plc`).

RuSTy compiles ST to native code with LLVM; its standard library
(`libs/stdlib`, Rust) implements the timers against `std::time::Instant`,
with a `mock_time` cargo feature that replaces the clock by one settable
through the C symbols `__mock_time_set_ns`. The harness therefore needs the
stdlib built with that feature:

    cd rusty
    cargo build --release                                  # plc
    cargo build --release -p iec61131std --features mock_time

For each test the harness:
  1. copies the .st, renames `PROGRAM main` to `PROGRAM conf_prog` (a program
     named `main` would clash with the C driver's `main`), and appends
     accessor FUNCTIONs `__set_<in>`, `__get_<out>` and `__run` (which calls
     the program) so the driver never depends on the instance struct layout;
  2. compiles with `plc -c` plus the stdlib ST declarations;
  3. links a generated C driver with the object and `libiec61131std.a`;
  4. runs it on the trace records with simulated time, compares.

Usage:
  run.py --plc PATH --rusty-src PATH [--record] [--keep] DIR_OR_FILE...
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "matiec"))
from tracefmt import Status, parse_trace  # noqa: E402

# IEC type -> (C type for the accessor ABI, printf, literal from trace text)
C_TYPES = {
    "BOOL": "unsigned char",
    "INT": "short",
    "DINT": "int",
    "UINT": "unsigned short",
    "TIME": "int",  # RuSTy TIME is a 32-bit millisecond count in this build (see IR: ET is i32)
    "BYTE": "unsigned char",
    "WORD": "unsigned short",
    "DWORD": "unsigned int",
    "REAL": "float",
    "LREAL": "double",
}
HEX_WIDTH = {"BYTE": 2, "WORD": 4, "DWORD": 8}
REAL_FMT = {"REAL": "%.9g", "LREAL": "%.17g"}

DRIVER = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <setjmp.h>

void __mock_time_set_ns(unsigned long long ns);
int __run(void);
%(decls)s

static jmp_buf trap_env;
static void on_sig(int sig) { (void)sig; longjmp(trap_env, 1); }

%(setters)s
%(getters)s

int main(void) {
    signal(SIGFPE, on_sig);
    signal(SIGSEGV, on_sig);
    signal(SIGILL, on_sig);
    signal(SIGABRT, on_sig);
    char line[4096];
    unsigned long cycle = 0;
    while (fgets(line, sizeof line, stdin)) {
        char *save = NULL;
        char *tok = strtok_r(line, " \t\r\n", &save);
        if (!tok) continue;
        cycle = strtoul(tok, NULL, 10);
        while ((tok = strtok_r(NULL, " \t\r\n", &save))) {
            char *eq = strchr(tok, '=');
            if (!eq) continue;
            *eq = 0;
            set_input(tok, eq + 1);
        }
        __mock_time_set_ns((unsigned long long)cycle * %(period)d * 1000000ULL);
        if (setjmp(trap_env) == 0) {
            __run();
        } else {
            printf("%%lu => trap   # signal\n", cycle);
            fflush(stdout);
            return 0;
        }
        printf("%%lu =>", cycle);
        print_outputs();
        printf("\n");
        fflush(stdout);
    }
    return 0;
}
'''


def st_literal(ty):
    return {"BOOL": "BOOL", "INT": "INT", "DINT": "DINT", "UINT": "UINT", "TIME": "TIME",
            "BYTE": "BYTE", "WORD": "WORD", "DWORD": "DWORD", "REAL": "REAL", "LREAL": "LREAL"}[ty]


def accessors_st(inputs, outputs):
    """ST functions appended to the program copy."""
    parts = []
    for n, ty in inputs:
        parts.append(
            f"FUNCTION __set_{n} : DINT\n  VAR_INPUT v : {ty}; END_VAR\n"
            f"  conf_prog.{n} := v;\n  __set_{n} := 0;\nEND_FUNCTION\n")
    for n, ty in outputs:
        parts.append(
            f"FUNCTION __get_{n} : {ty}\n  __get_{n} := conf_prog.{n};\nEND_FUNCTION\n")
    parts.append("FUNCTION __run : DINT\n  conf_prog();\n  __run := 0;\nEND_FUNCTION\n")
    return "\n".join(parts)


def c_decls(inputs, outputs):
    lines = []
    for n, ty in inputs:
        lines.append(f"int __set_{n}({C_TYPES[ty]});")
    for n, ty in outputs:
        lines.append(f"{C_TYPES[ty]} __get_{n}(void);")
    return "\n".join(lines)


def c_setters(inputs):
    cases = []
    for n, ty in inputs:
        if ty == "BOOL":
            cases.append(f'    if (!strcmp(name, "{n}")) {{ __set_{n}(!strcmp(text, "TRUE")); return; }}')
        elif ty == "TIME":
            cases.append(f'    if (!strcmp(name, "{n}")) {{ __set_{n}((int)atoll(text + 2)); return; }}')
        elif ty in HEX_WIDTH:
            cases.append(f'    if (!strcmp(name, "{n}")) {{ __set_{n}(({C_TYPES[ty]})strtoull(text + 3, NULL, 16)); return; }}')
        elif ty in REAL_FMT:
            cases.append(f'    if (!strcmp(name, "{n}")) {{ __set_{n}(({C_TYPES[ty]})strtod(text, NULL)); return; }}')
        else:
            cases.append(f'    if (!strcmp(name, "{n}")) {{ __set_{n}(({C_TYPES[ty]})atoll(text)); return; }}')
    body = "\n".join(cases)
    return f'static void set_input(const char *name, const char *text) {{\n{body}\n    fprintf(stderr, "unknown input %s\\n", name); exit(2);\n}}'


def c_getters(outputs):
    lines = []
    for n, ty in outputs:
        if ty == "BOOL":
            lines.append(f'    printf(" {n}=%s", __get_{n}() ? "TRUE" : "FALSE");')
        elif ty == "TIME":
            lines.append(f'    printf(" {n}=T#%dms", __get_{n}());')
        elif ty in HEX_WIDTH:
            lines.append(f'    printf(" {n}=16#%0{HEX_WIDTH[ty]}llX", (unsigned long long)__get_{n}());')
        elif ty in REAL_FMT:
            lines.append(f'    printf(" {n}={REAL_FMT[ty]}", (double)__get_{n}());')
        else:
            lines.append(f'    printf(" {n}=%lld", (long long)__get_{n}());')
    body = "\n".join(lines)
    return f"static void print_outputs(void) {{\n{body}\n}}"


def declared_types(st_text, program):
    m = re.search(r"PROGRAM\s+" + re.escape(program) + r"\b(.*?)END_PROGRAM", st_text, re.S | re.I)
    if not m:
        raise RuntimeError(f"PROGRAM {program} not found")
    body = re.sub(r"\(\*.*?\*\)", "", m.group(1), flags=re.S)
    types = {}
    for sect in re.finditer(r"VAR(?:_INPUT|_OUTPUT)?\s*(.*?)END_VAR", body, re.S | re.I):
        for decl in sect.group(1).split(";"):
            if ":" not in decl:
                continue
            names, ty = decl.split(":", 1)
            ty = ty.split(":=")[0].strip().upper()
            for n in names.split(","):
                n = n.strip().lower()
                if n:
                    types[n] = ty
    return types


def run_test(st_path: Path, opts):
    trace = parse_trace(st_path.with_suffix(".trace").read_text())
    st_text = st_path.read_text()
    types = declared_types(st_text, trace.program)
    for n in trace.inputs + trace.outputs:
        if types.get(n) not in C_TYPES:
            return "ERROR", [f"variable {n}: unsupported or undeclared type {types.get(n)}"], []
    inputs = [(n, types[n]) for n in trace.inputs]
    outputs = [(n, types[n]) for n in trace.outputs]

    rusty = Path(opts.rusty_src)
    stdlib_st = sorted((rusty / "libs" / "stdlib" / "iec61131-st").glob("*.st"))
    stdlib_a = rusty / "target" / "release" / "libiec61131std.a"
    if not stdlib_a.exists():
        return "ERROR", [f"{stdlib_a} not found: build it with --features mock_time"], []

    work = Path(tempfile.mkdtemp(prefix="rusty-" + st_path.stem + "-"))
    try:
        src = re.sub(r"PROGRAM\s+" + re.escape(trace.program) + r"\b", "PROGRAM conf_prog", st_text, flags=re.I)
        src += "\n\n" + accessors_st(inputs, outputs)
        (work / "prog.st").write_text(src)
        r = subprocess.run([opts.plc, "-c", "prog.st", "-o", "prog.o"] + [a for p in stdlib_st for a in ("-i", str(p))],
                           cwd=work, capture_output=True, text=True)
        if r.returncode != 0:
            return ("FAIL" if trace.status == Status.CONFORMANT else "DIFFERS"), ["plc failed to compile the program:\n" + (r.stdout + r.stderr)[:3000]], []
        (work / "driver.c").write_text(DRIVER % {
            "decls": c_decls(inputs, outputs),
            "setters": c_setters(inputs),
            "getters": c_getters(outputs),
            "period": trace.period_ms,
        })
        r = subprocess.run(["gcc", "-O0", "-w", "-no-pie", "-o", "driver", "driver.c", "prog.o", str(stdlib_a),
                            "-lpthread", "-ldl", "-lm"], cwd=work, capture_output=True, text=True)
        if r.returncode != 0:
            return "ERROR", ["gcc failed:\n" + r.stderr[:3000]], []
        stdin = "".join(
            f"{rec.cycle} " + " ".join(f"{n}={v}" for n, v in rec.inputs) + "\n" for rec in trace.records)
        r = subprocess.run(["./driver"], cwd=work, input=stdin, capture_output=True, text=True, timeout=60)
        actual_lines = [l for l in r.stdout.splitlines() if l.strip()]
    finally:
        if not opts.keep:
            shutil.rmtree(work, ignore_errors=True)
        else:
            print(f"        kept {work}")

    problems, recorded = [], []
    by_cycle = {int(l.split()[0]): l for l in actual_lines}
    for rec in trace.records:
        got = by_cycle.get(rec.cycle)
        inp = "".join(f" {n}={v}" for n, v in rec.inputs)
        if got is None:
            problems.append(f"cycle {rec.cycle}: no output (program crashed? rc={r.returncode}, stderr={r.stderr.strip()[:200]})")
            break
        rhs = got.split("=>", 1)[1].strip()
        recorded.append(f"{rec.cycle}{inp} => {rhs}")
        if rhs.startswith("trap"):
            if rec.expected != "trap":
                problems.append(f"cycle {rec.cycle} (trace line {rec.line}): unexpected trap ({rhs})")
            break
        if rec.expected == "trap":
            problems.append(f"cycle {rec.cycle} (trace line {rec.line}): expected a trap, got {rhs}")
            continue
        actual = dict(tok.split("=", 1) for tok in rhs.split())
        for name, value in rec.expected:
            if value.kind == "any":
                continue
            if not value.matches(actual.get(name), types[name]):
                problems.append(f"cycle {rec.cycle} (trace line {rec.line}): {name} expected {value}, got {actual.get(name)}")
    if trace.status == Status.CONFORMANT:
        return ("PASS" if not problems else "FAIL"), problems, recorded
    return ("SAME" if not problems else "DIFFERS"), problems, recorded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plc", required=True, help="path to the RuSTy `plc` binary")
    ap.add_argument("--rusty-src", required=True, help="RuSTy checkout (for libs/stdlib and target/release/libiec61131std.a)")
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("paths", nargs="+")
    opts = ap.parse_args()
    tests = []
    for p in opts.paths:
        p = Path(p)
        tests += sorted(p.rglob("*.st")) if p.is_dir() else [p]
    counts = {"PASS": 0, "FAIL": 0, "SAME": 0, "DIFFERS": 0, "ERROR": 0}
    for st in tests:
        try:
            verdict, problems, recorded = run_test(st, opts)
        except Exception as e:
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
