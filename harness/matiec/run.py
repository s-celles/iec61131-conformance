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
     The driver also defines the `iec_lib_*` math entry points that lib/C
     declares and leaves to the runtime (Beremiz provides them normally).

Usage:
  run.py --iec2c PATH --matiec-lib PATH [--record] DIR_OR_FILE...

Exit status: 0 when every conformant test passes, 1 otherwise, 2 on a
harness error (iec2c or gcc failure is reported per test, not fatal).

Platform note: the recorded evidence (notes/evidence/matiec-run.txt) is from
Linux x86-64 with gcc, which is what CI runs. On macOS/arm64 two tests come
out differently for reasons outside the suite: integer division by zero does
not trap on AArch64 (undefined/div_zero reports values instead of a trap),
and clang rejects the implicit function declaration iec2c emits for a user
FUNCTION called before its definition (undefined/eval_order fails to build).
Both are reported upstream: beremiz/matiec#38 (division) and #39 (guard).
For REAL tests the Linux glibc prints NaN as `-nan` where macOS prints
`nan`, so those sections of the evidence also come from the CI artifact.
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
from tracefmt import Status, Value, canonical_actual, parse_trace  # noqa: E402

TYPE_C = {"BOOL": "BOOL", "INT": "INT", "DINT": "DINT", "UINT": "UINT", "TIME": "TIME",
          "BYTE": "BYTE", "WORD": "WORD", "DWORD": "DWORD", "REAL": "REAL", "LREAL": "LREAL"}
REAL_FMT = {"REAL": "%.9g", "LREAL": "%.17g"}
HEX_WIDTH = {"BYTE": 2, "WORD": 4, "DWORD": 8}

DRIVER = r'''
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <setjmp.h>
#include <string.h>
#include <math.h>
#include <stdarg.h>
#include "iec_std_lib.h"

/* Math and C-library entry points that matiec's lib/C declares and expects
   the runtime (normally Beremiz's) to provide. */
double iec_lib_acos(double x) { return acos(x); }
double iec_lib_asin(double x) { return asin(x); }
double iec_lib_atan(double x) { return atan(x); }
double iec_lib_cos(double x) { return cos(x); }
double iec_lib_exp(double x) { return exp(x); }
double iec_lib_fmod(double x, double y) { return fmod(x, y); }
double iec_lib_log(double x) { return log(x); }
double iec_lib_log10(double x) { return log10(x); }
double iec_lib_pow(double x, double y) { return pow(x, y); }
double iec_lib_sin(double x) { return sin(x); }
double iec_lib_sqrt(double x) { return sqrt(x); }
double iec_lib_tan(double x) { return tan(x); }
int iec_lib_snprintf(char *s, size_t n, const char *f, ...) {
    va_list ap; va_start(ap, f); int r = vsnprintf(s, n, f, ap); va_end(ap); return r;
}
#include "accessor.h"
#include "POUS.h"

TIME __CURRENT_TIME;
%(externs)s
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
            /* matiec counts ticks of the common tick time (gcd of the task
               intervals); the trace step must be a multiple of it */
            if (t_ms %% %(common)d == 0) config_run__((unsigned long)(t_ms / %(common)d));
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
    """Generate set_input(name, text) for the declared inputs: (name, type, C lvalue)."""
    cases = []
    for name, ty, lv in inputs:
        if ty == "BOOL":
            cases.append(f'    if (!strcmp(name, "{name}")) {{ {lv} = !strcmp(text, "TRUE"); return; }}')
        elif ty == "TIME":
            cases.append(f'    if (!strcmp(name, "{name}")) {{ long long ms = atoll(text + 2); {lv}.tv_sec = ms / 1000; {lv}.tv_nsec = (int32_t)((ms % 1000) * 1000000); return; }}')
        elif ty in HEX_WIDTH:
            cases.append(f'    if (!strcmp(name, "{name}")) {{ {lv} = ({TYPE_C[ty]})strtoull(text + 3, NULL, 16); return; }}')
        elif ty in REAL_FMT:
            cases.append(f'    if (!strcmp(name, "{name}")) {{ {lv} = ({TYPE_C[ty]})strtod(text, NULL); return; }}')
        else:
            cases.append(f'    if (!strcmp(name, "{name}")) {{ {lv} = ({TYPE_C[ty]})atoll(text); return; }}')
    body = "\n".join(cases)
    return f'static void set_input(const char *name, const char *text) {{\n{body}\n    fprintf(stderr, "unknown input %s\\n", name); exit(2);\n}}'


def c_getters(outputs):
    lines = []
    for name, ty, lv in outputs:
        if ty == "BOOL":
            lines.append(f'    printf(" {name}=%s", {lv} ? "TRUE" : "FALSE");')
        elif ty == "TIME":
            lines.append(f'    printf(" {name}="); print_time({lv});')
        elif ty in HEX_WIDTH:
            lines.append(f'    printf(" {name}=16#%0{HEX_WIDTH[ty]}llX", (unsigned long long){lv});')
        elif ty in REAL_FMT:
            lines.append(f'    printf(" {name}={REAL_FMT[ty]}", (double){lv});')
        elif ty.startswith("STRING"):
            lines.append(f'    printf(" {name}=#"); for (int i = 0; i < {lv}.len; i++) printf("%02X", (unsigned){lv}.body[i]);')
        else:
            lines.append(f'    printf(" {name}=%lld", (long long){lv});')
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
    # named string types: TYPE S5 : STRING[5]; END_TYPE
    aliases = {}
    for tb in re.finditer(r"\bTYPE\b(.*?)END_TYPE", st_text, re.S | re.I):
        for m in re.finditer(r"(\w+)\s*:\s*(STRING(?:\s*\[\s*\d+\s*\])?)\s*(?::=[^;]*)?;", tb.group(1), re.I):
            aliases[m.group(1).upper()] = m.group(2).upper().replace(" ", "")
    for n, ty in types.items():
        if ty in aliases:
            types[n] = aliases[ty]
    return types


def parse_configuration(st_text):
    """SPEC.md version 2: a CONFIGURATION in the .st. Returns None or a dict
    with the configuration and resource names, the program instances
    (name -> program type) and the VAR_GLOBAL types."""
    text = re.sub(r"\(\*.*?\*\)", "", st_text, flags=re.S)
    m = re.search(r"\bCONFIGURATION\s+(\w+)(.*?)END_CONFIGURATION", text, re.S | re.I)
    if not m:
        return None
    conf, body = m.group(1), m.group(2)
    r = re.search(r"\bRESOURCE\s+(\w+)\s+ON\b", body, re.I)
    res = r.group(1) if r else None
    instances = {i.group(1).lower(): i.group(3)
                 for i in re.finditer(r"\bPROGRAM\s+(\w+)\s+WITH\s+(\w+)\s*:\s*(\w+)\s*;", body, re.I)}
    globals_ = {}
    for g in re.finditer(r"VAR_GLOBAL\b(.*?)END_VAR", body, re.S | re.I):
        for decl in g.group(1).split(";"):
            if ":" not in decl:
                continue
            names, ty = decl.split(":", 1)
            ty = ty.split(":=")[0].strip().upper()
            for n in names.split(","):
                n = n.strip().lower()
                if n:
                    globals_[n] = ty
    return {"conf": conf, "res": res, "instances": instances, "globals": globals_}


def resolve_names(st_text, trace):
    """Trace names -> (type, C lvalue, extern declaration) for the driver.
    Version 1: program variables of the single instance RES0__INST0.
    Version 2: a global `g` is <CONF>__G.value, an instance variable
    `inst.v` is <RES>__<INST>.V.value."""
    conf = parse_configuration(st_text)
    out, externs = {}, []
    if conf is None:
        types = declared_types(st_text, trace.program)
        externs.append(f"extern {trace.program.upper()}_data__ RES0__INST0;")
        for n in trace.inputs + trace.outputs:
            if n in types:
                out[n] = (types[n], f"RES0__INST0.{n.upper()}.value")
        return conf, out, externs
    C, R = conf["conf"].upper(), (conf["res"] or "").upper()
    prog_types = {}
    for n in trace.inputs + trace.outputs:
        if "." in n:
            inst, var = n.split(".", 1)
            ptype = conf["instances"].get(inst)
            if ptype is None:
                continue
            if inst not in prog_types:
                prog_types[inst] = declared_types(st_text, ptype)
                externs.append(f"extern {ptype.upper()}_data__ {R}__{inst.upper()};")
            if var in prog_types[inst]:
                out[n] = (prog_types[inst][var], f"{R}__{inst.upper()}.{var.upper()}.value")
        elif n in conf["globals"]:
            ty = conf["globals"][n]
            cty = "STRING" if ty.startswith("STRING") else ty
            externs.append(f"extern __IEC_{cty}_t {C}__{n.upper()};")
            out[n] = (ty, f"{C}__{n.upper()}.value")
    return conf, out, externs


def run_test(st_path: Path, opts):
    trace = parse_trace((st_path.with_suffix(".trace")).read_text())
    st_text = st_path.read_text()
    conf, resolved, externs = resolve_names(st_text, trace)
    types = {n: t for n, (t, _) in resolved.items()}
    for n in trace.inputs + trace.outputs:
        if n not in types:
            return "ERROR", [f"variable {n} not declared (program {trace.program or '-'}, or not a global / instance.var of the configuration)"], []
        if types[n].startswith("STRING"):
            if n in trace.inputs:
                return "ERROR", [f"variable {n}: STRING inputs are not supported (SPEC.md)"], []
            continue
        if types[n] not in TYPE_C:
            return "ERROR", [f"variable {n} has unsupported type {types[n]}"], []

    work = Path(tempfile.mkdtemp(prefix="matiec-" + st_path.stem + "-"))
    try:
        if conf is None:
            src = st_text + (
                "\n\nCONFIGURATION config\n  RESOURCE res0 ON PLC\n"
                f"    TASK t0(INTERVAL := T#{trace.period_ms}ms, PRIORITY := 0);\n"
                f"    PROGRAM inst0 WITH t0 : {trace.program};\n"
                "  END_RESOURCE\nEND_CONFIGURATION\n"
            )
            conf_c, res_c = "config.c", "res0.c"
        else:
            src = st_text
            conf_c, res_c = conf["conf"].lower() + ".c", (conf["res"] or "res0").lower() + ".c"
        (work / "prog.st").write_text(src)
        r = subprocess.run([opts.iec2c, "-I", opts.matiec_lib, "prog.st"], cwd=work,
                           capture_output=True, text=True)
        if r.returncode != 0:
            return ("FAIL" if trace.status == Status.CONFORMANT else "DIFFERS"), ["iec2c failed to compile the program:\n" + r.stdout + r.stderr], []
        m = re.search(r"__DECLARE_CONFIGURATION\(\w+,\s*(\d+)\)", (work / "GLOBALS.h").read_text())
        common_ms = int(m.group(1)) // 1000000 if m else trace.period_ms
        if common_ms == 0 or trace.period_ms % common_ms != 0:
            return "ERROR", [f"trace step {trace.period_ms} ms is not a multiple of the configuration's common tick {common_ms} ms"], []
        driver = DRIVER % {
            "externs": "\n".join(externs),
            "period": trace.period_ms,
            "common": common_ms,
            "setters": c_setters([(n, types[n], resolved[n][1]) for n in trace.inputs]),
            "getters": c_getters([(n, types[n], resolved[n][1]) for n in trace.outputs]),
        }
        (work / "driver.c").write_text(driver)
        r = subprocess.run(["gcc", "-O0", "-w", "-I", str(Path(opts.matiec_lib) / "C"), "-I", ".",
                            "-o", "driver", "driver.c", conf_c, res_c, "-lm"],
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
        recorded.append(f"{rec.cycle}{inp} => {canonical_actual(rhs, types)}")
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
                problems.append(f"cycle {rec.cycle} (trace line {rec.line}): {name} expected {value}, got {canonical_actual(f'{name}={actual.get(name)}', types).split('=', 1)[1]}")
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
