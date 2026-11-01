#!/usr/bin/env python3
"""Runs the conformance traces against matiec (iec2c) generated C code.

This is the differential-testing harness: the same .st/.trace pairs, a
different runtime. For each test it

  1. appends a CONFIGURATION with one cyclic task at the trace period,
  2. runs `iec2c` to generate C,
  3. generates a small C driver that sets __CURRENT_TIME to cycle * period,
     writes the inputs of the record into the program instance
     (RES0__INST0.<NAME>.value), calls config_run__(tick) once, and prints
     the outputs in .trace record syntax,
  4. compiles with gcc against matiec's lib/C, runs it, and compares.

Usage:
  run.py --iec2c PATH --matiec-lib PATH [--record] DIR_OR_FILE...

Exit status: 0 when every conformant test passes, 1 otherwise, 2 on a
harness error (iec2c or gcc failure is reported per test, not fatal).
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tracefmt import Status, Value, parse_trace  # noqa: E402

TYPE_C = {"BOOL": "BOOL", "INT": "INT", "DINT": "DINT", "UINT": "UINT", "TIME": "TIME"}

DRIVER = r'''
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <setjmp.h>
#include <string.h>
#include "iec_std_lib.h"
#include "accessor.h"
#include "POUS.h"

TIME __CURRENT_TIME;
extern %(prog)s_data__ RES0__INST0;
void config_init__(void);
void config_run__(unsigned long tick);

static jmp_buf trap_env;
static void on_sigfpe(int sig) { (void)sig; longjmp(trap_env, 1); }

static void print_time(TIME t) {
    long long ms = (long long)t.tv_sec * 1000 + t.tv_nsec / 1000000;
    printf("T#%%lldms", ms);
}

%(setters)s
%(getters)s

int main(void) {
    signal(SIGFPE, on_sigfpe);
    __CURRENT_TIME.tv_sec = 0; __CURRENT_TIME.tv_nsec = 0;
    config_init__();
    char line[4096];
    unsigned long cycle = 0;
    while (fgets(line, sizeof line, stdin)) {
        /* line: <cycle> name=value ... ; apply inputs, then run one cycle */
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
        long long t_ms = (long long)cycle * %(period)d;
        __CURRENT_TIME.tv_sec = t_ms / 1000;
        __CURRENT_TIME.tv_nsec = (int32_t)((t_ms %% 1000) * 1000000);
        if (setjmp(trap_env) == 0) {
            config_run__(cycle);
        } else {
            printf("%%lu => trap   # SIGFPE\n", cycle);
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


def c_setters(inputs):
    """Generate set_input(name, text) for the declared inputs."""
    cases = []
    for name, ty in inputs:
        cname = name.upper()
        if ty == "BOOL":
            cases.append(f'    if (!strcmp(name, "{name}")) {{ RES0__INST0.{cname}.value = !strcmp(text, "TRUE"); return; }}')
        elif ty == "TIME":
            cases.append(f'    if (!strcmp(name, "{name}")) {{ long long ms = atoll(text + 2); RES0__INST0.{cname}.value.tv_sec = ms / 1000; RES0__INST0.{cname}.value.tv_nsec = (int32_t)((ms % 1000) * 1000000); return; }}')
        else:
            cases.append(f'    if (!strcmp(name, "{name}")) {{ RES0__INST0.{cname}.value = ({TYPE_C[ty]})atoll(text); return; }}')
    body = "\n".join(cases)
    return f'static void set_input(const char *name, const char *text) {{\n{body}\n    fprintf(stderr, "unknown input %s\\n", name); exit(2);\n}}'


def c_getters(outputs):
    lines = []
    for name, ty in outputs:
        cname = name.upper()
        if ty == "BOOL":
            lines.append(f'    printf(" {name}=%s", RES0__INST0.{cname}.value ? "TRUE" : "FALSE");')
        elif ty == "TIME":
            lines.append(f'    printf(" {name}="); print_time(RES0__INST0.{cname}.value);')
        else:
            lines.append(f'    printf(" {name}=%lld", (long long)RES0__INST0.{cname}.value);')
    body = "\n".join(lines)
    return f"static void print_outputs(void) {{\n{body}\n}}"


def declared_types(st_text, program):
    """Map lower-case variable name -> type for the program's VAR sections."""
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
    trace = parse_trace((st_path.with_suffix(".trace")).read_text())
    st_text = st_path.read_text()
    types = declared_types(st_text, trace.program)
    for n in trace.inputs + trace.outputs:
        if n not in types:
            return "ERROR", [f"variable {n} not declared in PROGRAM {trace.program}"], []
        if types[n] not in TYPE_C:
            return "ERROR", [f"variable {n} has unsupported type {types[n]}"], []

    work = Path(tempfile.mkdtemp(prefix="matiec-" + st_path.stem + "-"))
    try:
        src = st_text + (
            "\n\nCONFIGURATION config\n  RESOURCE res0 ON PLC\n"
            f"    TASK t0(INTERVAL := T#{trace.period_ms}ms, PRIORITY := 0);\n"
            f"    PROGRAM inst0 WITH t0 : {trace.program};\n"
            "  END_RESOURCE\nEND_CONFIGURATION\n"
        )
        (work / "prog.st").write_text(src)
        r = subprocess.run([opts.iec2c, "-I", opts.matiec_lib, "prog.st"], cwd=work,
                           capture_output=True, text=True)
        if r.returncode != 0:
            return ("FAIL" if trace.status == Status.CONFORMANT else "DIFFERS"), ["iec2c failed to compile the program:\n" + r.stdout + r.stderr], []
        driver = DRIVER % {
            "prog": trace.program.upper(),
            "period": trace.period_ms,
            "setters": c_setters([(n, types[n]) for n in trace.inputs]),
            "getters": c_getters([(n, types[n]) for n in trace.outputs]),
        }
        (work / "driver.c").write_text(driver)
        r = subprocess.run(["gcc", "-O0", "-w", "-I", str(Path(opts.matiec_lib) / "C"), "-I", ".",
                            "-o", "driver", "driver.c", "config.c", "res0.c", "-lm"],
                           cwd=work, capture_output=True, text=True)
        if r.returncode != 0:
            return "ERROR", ["gcc failed:\n" + r.stderr[:3000]], []
        stdin = "".join(
            f"{rec.cycle} " + " ".join(f"{n}={v}" for n, v in rec.inputs) + "\n" for rec in trace.records
        )
        r = subprocess.run(["./driver"], cwd=work, input=stdin, capture_output=True, text=True, timeout=60)
        actual_lines = [l for l in r.stdout.splitlines() if l.strip()]
    finally:
        if not opts.keep:
            shutil.rmtree(work, ignore_errors=True)

    problems = []
    recorded = []
    actual_by_cycle = {}
    for l in actual_lines:
        cyc = int(l.split()[0])
        actual_by_cycle[cyc] = l
    for rec in trace.records:
        got = actual_by_cycle.get(rec.cycle)
        inp = "".join(f" {n}={v}" for n, v in rec.inputs)
        if got is None:
            problems.append(f"cycle {rec.cycle}: no output (program crashed? rc={r.returncode})")
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
            if actual.get(name) != str(value):
                problems.append(f"cycle {rec.cycle} (trace line {rec.line}): {name} expected {value}, got {actual.get(name)}")
    if trace.status == Status.CONFORMANT:
        return ("PASS" if not problems else "FAIL"), problems, recorded
    return ("SAME" if not problems else "DIFFERS"), problems, recorded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iec2c", required=True)
    ap.add_argument("--matiec-lib", required=True, help="matiec/lib directory (contains C/ and the .txt bodies)")
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--keep", action="store_true", help="keep the temporary build directories")
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
