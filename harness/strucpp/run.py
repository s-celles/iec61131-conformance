#!/usr/bin/env python3
"""Runs the conformance traces against STruC++ (Autonomy-Logic/STruCpp), the
ST to C++14 compiler behind OpenPLC Runtime v4.

For each test the harness

  1. runs `strucpp prog.st -o prog.cpp`, which writes prog.cpp and prog.hpp:
     a class Program_<NAME> with a run() method and one IECVar member per
     variable, and, when the .st has a CONFIGURATION, a
     Configuration_<NAME> holding the program instances and file-scope
     GlobalVar<...> globals;
  2. generates a C++ driver that instantiates the program (or the
     configuration), writes the inputs of each record (IECVar::set,
     GlobalVar::write), sets the runtime's scan clock
     (strucpp::__CURRENT_TIME_NS, nanoseconds), runs the cycle and prints
     the outputs in .trace record syntax;
  3. compiles both with g++ -std=c++14 against the header-only runtime
     (--runtime-include, STruCpp's src/runtime/include), runs it, compares.

Configurations (SPEC.md version 2): STruC++ ships no scheduler usable with a
simulated clock (its --build REPL loop, iec_cyclic.hpp, sleeps in real time),
so the driver reproduces that loop's rule: at every step, each periodic task
whose interval divides the time runs its programs, in the order the tasks are
declared, priority ignored; a SINGLE task (interval 0) is not driven and the
test is reported as an error. What is tested is therefore STruC++'s compiled
programs and globals, not a scheduler of its own.

Usage:
  run.py --strucpp "node /path/to/STruCpp/dist/node/cli.js" \
         --runtime-include /path/to/STruCpp/src/runtime/include \
         [--record] [--keep] DIR_OR_FILE...

Exit status: 0 when every conformant test passes, 1 otherwise, 2 on a
harness error.
"""
import argparse
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "matiec"))
from run import declared_types, parse_configuration  # noqa: E402
from tracefmt import Status, canonical_actual, parse_trace  # noqa: E402

# IEC type -> (C++ scalar for casts, printf format)
SCALAR = {
    "BOOL": "bool",
    "INT": "int16_t", "DINT": "int32_t", "UINT": "uint16_t",
    "BYTE": "uint8_t", "WORD": "uint16_t", "DWORD": "uint32_t",
    "REAL": "float", "LREAL": "double",
    "TIME": "int64_t",
}
HEX_WIDTH = {"BYTE": 2, "WORD": 4, "DWORD": 8}
REAL_FMT = {"REAL": "%.9g", "LREAL": "%.17g"}

DRIVER = r'''
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <csignal>
#include <csetjmp>
#include <exception>
#include "prog.hpp"

using namespace strucpp;

%(instances)s

static jmp_buf trap_env;
static void on_sigfpe(int sig) { (void)sig; longjmp(trap_env, 1); }

static void set_input(const char *name, const char *text) {
%(setters)s
    fprintf(stderr, "unknown input %%s\n", name); exit(2);
}

static void print_outputs(void) {
%(getters)s
}

static void run_cycle(long long t_ms) {
%(dispatch)s
}

int main(void) {
    signal(SIGFPE, on_sigfpe);
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
        long long t_ms = (long long)cycle * %(period)d;
        __CURRENT_TIME_NS = t_ms * 1000000LL;
        if (setjmp(trap_env) == 0) {
            try {
                run_cycle(t_ms);
            } catch (const std::exception &e) {
                printf("%%lu => trap   # %%s\n", cycle, e.what());
                fflush(stdout);
                return 0;
            }
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


def setter(name, ty, lv, is_global):
    """C++ statement writing the trace text `text` into the variable."""
    if ty == "BOOL":
        value = '!strcmp(text, "TRUE")'
    elif ty == "TIME":
        value = "(int64_t)atoll(text + 2) * 1000000LL"
    elif ty in HEX_WIDTH:
        value = f"({SCALAR[ty]})strtoull(text + 3, NULL, 16)"
    elif ty in REAL_FMT:
        value = f"({SCALAR[ty]})strtod(text, NULL)"
    else:
        value = f"({SCALAR[ty]})atoll(text)"
    write = f"{lv}.write({value})" if is_global else f"{lv}.set({value})"
    return f'    if (!strcmp(name, "{name}")) {{ {write}; return; }}'


def getter(name, ty, lv, is_global):
    read = f"{lv}.read().get()" if is_global else f"{lv}.get()"
    if ty == "BOOL":
        return f'    printf(" {name}=%s", {read} ? "TRUE" : "FALSE");'
    if ty == "TIME":
        return f'    printf(" {name}=T#%lldms", (long long)({read} / 1000000LL));'
    if ty in HEX_WIDTH:
        return f'    printf(" {name}=16#%0{HEX_WIDTH[ty]}llX", (unsigned long long){read});'
    if ty in REAL_FMT:
        return f'    printf(" {name}={REAL_FMT[ty]}", (double){read});'
    if ty.startswith("STRING"):
        return (f'    {{ auto s = {read}; printf(" {name}=#"); '
                f'for (size_t i = 0; i < s.length(); i++) printf("%02X", (unsigned char)s.c_str()[i]); }}')
    return f'    printf(" {name}=%lld", (long long){read});'


def resolve(st_text, trace):
    """Trace names -> (type, C++ lvalue, is_global); the instance declarations
    and the per-step dispatch of the driver."""
    conf = parse_configuration(st_text)
    out = {}
    if conf is None:
        types = declared_types(st_text, trace.program)
        for n in trace.inputs + trace.outputs:
            if n in types:
                out[n] = (types[n], f"prog.{n.upper()}", False)
        instances = f"static Program_{trace.program.upper()} prog;"
        dispatch = "    (void)t_ms;\n    prog.run();"
        return conf, out, instances, dispatch, None
    cname = conf["conf"].upper()
    prog_types = {}
    for n in trace.inputs + trace.outputs:
        if "." in n:
            inst, var = n.split(".", 1)
            ptype = conf["instances"].get(inst)
            if ptype is None:
                continue
            if inst not in prog_types:
                prog_types[inst] = declared_types(st_text, ptype)
            if var in prog_types[inst]:
                out[n] = (prog_types[inst][var], f"cfg.{inst.upper()}.{var.upper()}", False)
        elif n in conf["globals"]:
            out[n] = (conf["globals"][n], f"strucpp::{n.upper()}", True)
    # tasks in declaration order, as STruC++'s own cyclic loop runs them
    text = re.sub(r"\(\*.*?\*\)", "", st_text, flags=re.S)
    body = re.search(r"\bCONFIGURATION\s+\w+(.*?)END_CONFIGURATION", text, re.S | re.I).group(1)
    tasks = {}
    for t in re.finditer(r"\bTASK\s+(\w+)\s*\((.*?)\)\s*;", body, re.S | re.I):
        params = t.group(2)
        if re.search(r"\bSINGLE\b", params, re.I):
            return conf, out, None, None, f"task {t.group(1)} is SINGLE: not driven by this harness"
        m = re.search(r"INTERVAL\s*:=\s*T#(\d+)ms", params, re.I)
        tasks[t.group(1).lower()] = int(m.group(1)) if m else 0
    lines = []
    for i in re.finditer(r"\bPROGRAM\s+(\w+)\s+WITH\s+(\w+)\s*:\s*\w+\s*;", body, re.I):
        inst, task = i.group(1).upper(), i.group(2).lower()
        interval = tasks.get(task, 0)
        if interval <= 0:
            return conf, out, None, None, f"task {task} has no INTERVAL"
        lines.append(f"    if (t_ms % {interval} == 0) cfg.{inst}.run();")
    instances = f"static Configuration_{cname} cfg;"
    return conf, out, instances, "\n".join(lines), None


def run_test(st_path: Path, opts):
    trace = parse_trace(st_path.with_suffix(".trace").read_text())
    st_text = st_path.read_text()
    conf, resolved, instances, dispatch, problem = resolve(st_text, trace)
    if problem:
        return "ERROR", [problem], []
    types = {n: t for n, (t, _, _) in resolved.items()}
    for n in trace.inputs + trace.outputs:
        if n not in types:
            return "ERROR", [f"variable {n} not declared (program {trace.program or '-'}, or not a global / instance.var)"], []
        if types[n].startswith("STRING"):
            if n in trace.inputs:
                return "ERROR", [f"variable {n}: STRING inputs are not supported (SPEC.md)"], []
            continue
        if types[n] not in SCALAR:
            return "ERROR", [f"variable {n} has unsupported type {types[n]}"], []

    work = Path(tempfile.mkdtemp(prefix="strucpp-" + st_path.stem + "-"))
    try:
        shutil.copy(st_path, work / "prog.st")
        r = subprocess.run(shlex.split(opts.strucpp) + ["prog.st", "-o", "prog.cpp"], cwd=work,
                           capture_output=True, text=True)
        if r.returncode != 0 or not (work / "prog.hpp").exists():
            return ("FAIL" if trace.status == Status.CONFORMANT else "DIFFERS"), ["strucpp failed to compile the program:\n" + r.stdout + r.stderr], []
        driver = DRIVER % {
            "instances": instances,
            "period": trace.period_ms,
            "dispatch": dispatch,
            "setters": "\n".join(setter(n, *resolved[n]) for n in trace.inputs),
            "getters": "\n".join(getter(n, *resolved[n]) for n in trace.outputs),
        }
        (work / "driver.cpp").write_text(driver)
        r = subprocess.run(["g++", "-std=c++14", "-O0", "-w", "-I", opts.runtime_include, "-I", ".",
                            "-o", "driver", "prog.cpp", "driver.cpp"],
                           cwd=work, capture_output=True, text=True)
        if r.returncode != 0:
            return "ERROR", ["g++ failed:\n" + r.stderr[:3000]], []
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
    actual_by_cycle = {int(l.split()[0]): l for l in actual_lines}
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
    ap.add_argument("--strucpp", required=True, help="command running the compiler, e.g. 'node dist/node/cli.js'")
    ap.add_argument("--runtime-include", required=True, help="STruCpp's src/runtime/include")
    ap.add_argument("--record", action="store_true", help="print what the program produced, in .trace record syntax")
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
        except Exception as e:  # noqa: BLE001
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
