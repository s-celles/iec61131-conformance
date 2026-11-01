#!/usr/bin/env python3
"""Run conformance tests on Eclipse 4diac: the 4diac IDE's Structured Text
compiler (headless, through its Ant tasks) and the FORTE runtime library.

4diac implements IEC 61499; ST exists there as the algorithm of a basic
function block. Each test's PROGRAM is rewritten as one basic FB (.fbt):
VAR_INPUT -> data inputs, VAR_OUTPUT -> data outputs, VAR -> internal
variables, the body -> the algorithm of the state entered on the event REQ,
which emits CNF. The IDE exports the FB to C++ (forte_ng), a generated
driver instantiates it against libforte, and for each trace record sets the
inputs, fires REQ (one scan) and prints the outputs in trace syntax.

Scope: PROGRAM-only tests over the elementary types. No FUNCTION,
FUNCTION_BLOCK, TYPE or CONFIGURATION (reported as ERROR: 61499 has no ST
FB instances inside an algorithm, no timers in ST, no tasks), no STRING[n],
no simulated clock (nothing in this subset reads one).

    run.py --ide /path/to/4diac-ide.app \\
           --forte-src /path/to/4diac-forte --forte-build /path/to/4diac-forte/build \\
           [--record] [--keep] DIR_OR_FILE...

The IDE is launched once per invocation (all FBs in one project, one
export); a failing FB aborts the IDE's project export, in which case the
remaining FBs are exported one by one.
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "matiec"))
from tracefmt import Status, Value, canonical_actual, parse_trace  # noqa: E402

SCALAR = {
    "BOOL": ("CIEC_BOOL", "bool"), "INT": ("CIEC_INT", "TForteInt16"), "DINT": ("CIEC_DINT", "TForteInt32"),
    "UINT": ("CIEC_UINT", "TForteUInt16"), "BYTE": ("CIEC_BYTE", "TForteByte"), "WORD": ("CIEC_WORD", "TForteWord"),
    "DWORD": ("CIEC_DWORD", "TForteDWord"), "REAL": ("CIEC_REAL", "TForteFloat"), "LREAL": ("CIEC_LREAL", "TForteDFloat"),
    "TIME": ("CIEC_TIME", "TForteInt64"), "STRING": ("CIEC_STRING", "std::string"),
    # internal variables only (no trace value syntax): the date types
    "DATE": ("CIEC_DATE", None), "TOD": ("CIEC_TIME_OF_DAY", None), "TIME_OF_DAY": ("CIEC_TIME_OF_DAY", None),
    "DT": ("CIEC_DATE_AND_TIME", None), "DATE_AND_TIME": ("CIEC_DATE_AND_TIME", None),
}
HEX_WIDTH = {"BYTE": 2, "WORD": 4, "DWORD": 8}
REAL_FMT = {"REAL": "%.9g", "LREAL": "%.17g"}
UNSUPPORTED = ["FUNCTION_BLOCK", "CONFIGURATION", "VAR_GLOBAL", "VAR_EXTERNAL"]


class Unsupported(Exception):
    pass


def strip_comments(text):
    return re.sub(r"\(\*.*?\*\)", "", text, flags=re.S)


def parse_types(st_text):
    """-> {name: dtp xml} for the TYPE declarations: STRUCT and enumerations are
    4diac data types (.dtp); an array alias, a subrange or STRING[n] is not."""
    text = strip_comments(st_text)
    out = {}
    for tb in re.finditer(r"\bTYPE\b(.*?)\bEND_TYPE\b", text, re.S | re.I):
        body = tb.group(1)
        for m in re.finditer(r"(\w+)\s*:\s*(STRUCT\b(.*?)\bEND_STRUCT\s*;|\((.*?)\)\s*;|[^;]*;)", body, re.S | re.I):
            name, decl = m.group(1), m.group(2)
            if decl.upper().startswith("STRUCT"):
                members = []
                for d in m.group(3).split(";"):
                    if ":" not in d:
                        continue
                    n, rest = d.split(":", 1)
                    ty, init = (rest.split(":=", 1) + [None])[:2] if ":=" in rest else (rest, None)
                    ty = " ".join(ty.split()).upper()
                    am = re.match(r"ARRAY\s*\[\s*(-?\d+)\s*\.\.\s*(-?\d+)\s*\]\s*OF\s+(\w+)$", ty)
                    a = f' ArraySize="{am.group(1)}..{am.group(2)}"' if am else ""
                    if am:
                        ty = am.group(3)
                    i = f' InitialValue="{xml_escape(init.strip())}"' if init else ""
                    members.append(f'    <VarDeclaration Name="{n.strip()}" Type="{ty}"{a}{i}/>')
                kind = "StructuredType"
                inner = "\n".join(members)
            elif decl.startswith("("):
                kind = "EnumeratedType"
                inner = "\n".join(f'    <EnumeratedValue Name="{v.strip().split(':=')[0].strip()}"/>' for v in m.group(4).split(","))
            else:
                raise Unsupported(f"TYPE {name}: {' '.join(decl.split())} is not a 4diac data type (only STRUCT and enumerations are)")
            out[name] = f"""<?xml version="1.0" encoding="UTF-8"?>
<DataType Name="{name}" Comment="iec61131-conformance">
  <Identification Standard="61499-1"/>
  <VersionInfo Version="1.0" Author="harness" Date="2026-01-01"/>
  <{kind}>
{inner}
  </{kind}>
</DataType>
"""
    return out


def parse_functions(st_text):
    """-> {name: (return type, [(name, type)] inputs, [(name, type)] outputs, text)} for
    each FUNCTION of the file; the text goes verbatim into a 4diac .fct."""
    text = strip_comments(st_text)
    out = {}
    for m in re.finditer(r"\bFUNCTION\s+(\w+)\s*:\s*(\w+)(.*?)\bEND_FUNCTION\b", text, re.S | re.I):
        name, rtype, inner = m.group(1), m.group(2).upper(), m.group(3)
        if re.search(r"\bVAR_IN_OUT\b", inner, re.I):
            raise Unsupported(f"FUNCTION {name}: VAR_IN_OUT on a function is outside this harness's scope")
        ins, outs = [], []
        for sect in re.finditer(r"\b(VAR_INPUT|VAR_OUTPUT)\b\s*(.*?)\bEND_VAR\b", inner, re.S | re.I):
            for decl in sect.group(2).split(";"):
                if ":" not in decl:
                    continue
                names, rest = decl.split(":", 1)
                ty = rest.split(":=")[0].strip().upper()
                for n in names.split(","):
                    if n.strip():
                        (ins if sect.group(1).upper() == "VAR_INPUT" else outs).append((n.strip(), ty))
        out[name] = (rtype, ins, outs, m.group(0).strip())
    return out


def fct(name, rtype, ins, outs, text):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Function Name="{name}" Comment="iec61131-conformance">
  <Identification Standard="61499-1"/>
  <VersionInfo Version="1.0" Author="harness" Date="2026-01-01"/>
  <InterfaceList>
    <EventInputs>
      <Event Name="REQ" Type="Event">
{"".join(f'        <With Var="{n}"/>' + chr(10) for n, _ in ins)}      </Event>
    </EventInputs>
    <EventOutputs>
      <Event Name="CNF" Type="Event">
        <With Var=""/>
{"".join(f'        <With Var="{n}"/>' + chr(10) for n, _ in outs)}      </Event>
    </EventOutputs>
    <InputVars>
{chr(10).join(f'      <VarDeclaration Name="{n}" Type="{ty}"/>' for n, ty in ins)}
    </InputVars>
    <OutputVars>
      <VarDeclaration Name="" Type="{rtype}"/>
{chr(10).join(f'      <VarDeclaration Name="{n}" Type="{ty}"/>' for n, ty in outs)}
    </OutputVars>
  </InterfaceList>
  <FunctionBody>
    <ST><![CDATA[{text}]]></ST>
  </FunctionBody>
</Function>
"""


def parse_program(st_text, user_types=()):
    """-> (name, sections, body). sections: list of (kind, [(name, type, array, init)])."""
    text = strip_comments(st_text)
    text = re.sub(r"\bFUNCTION\s+\w+\s*:.*?\bEND_FUNCTION\b", "", text, flags=re.S | re.I)
    text = re.sub(r"\bTYPE\b.*?\bEND_TYPE\b", "", text, flags=re.S | re.I)
    for kw in UNSUPPORTED:
        if re.search(rf"^\s*{kw}\b", text, re.M | re.I):
            raise Unsupported(f"{kw} is outside this harness's scope (one PROGRAM over elementary types)")
    m = re.search(r"\bPROGRAM\s+(\w+)(.*?)END_PROGRAM", text, re.S | re.I)
    if not m:
        raise Unsupported("no PROGRAM found")
    name, inner = m.group(1), m.group(2)
    sections = []
    pos = 0
    for sect in re.finditer(r"\b(VAR_INPUT|VAR_OUTPUT|VAR_TEMP|VAR)\b\s*(?:CONSTANT\s*|RETAIN\s*)?(.*?)\bEND_VAR\b", inner, re.S | re.I):
        kind = sect.group(1).upper()
        decls = []
        for decl in sect.group(2).split(";"):
            if ":" not in decl:
                continue
            names, rest = decl.split(":", 1)
            ty, init = (rest.split(":=", 1) + [None])[:2] if ":=" in rest else (rest, None)
            ty = " ".join(ty.split()).upper()
            init = init.strip() if init else None
            array = None
            am = re.match(r"ARRAY\s*\[\s*(-?\d+)\s*\.\.\s*(-?\d+)\s*\]\s*OF\s+(\w+)$", ty)
            if am:
                array, ty = f"{am.group(1)}..{am.group(2)}", am.group(3)
            if ty.startswith("STRING["):
                raise Unsupported("STRING[n] is not a 4diac type")
            if ty not in SCALAR and ty not in {u.upper() for u in user_types}:
                raise Unsupported(f"type {ty} is outside this harness's scope")
            for n in names.split(","):
                n = n.strip()
                if n:
                    decls.append((n, ty, array, init))
        sections.append((kind, decls))
        pos = sect.end()
    body = inner[pos:].strip()
    return name, sections, body


def xml_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def fbt(fb_name, sections, body):
    ins = [d for k, ds in sections if k == "VAR_INPUT" for d in ds]
    outs = [d for k, ds in sections if k == "VAR_OUTPUT" for d in ds]
    internals = [d for k, ds in sections if k == "VAR" for d in ds]
    temps = [d for k, ds in sections if k == "VAR_TEMP" for d in ds]

    def var(d):
        n, ty, array, init = d
        a = f' ArraySize="{array}"' if array else ""
        i = f' InitialValue="{xml_escape(init)}"' if init else ""
        return f'      <VarDeclaration Name="{n}" Type="{ty}"{a}{i}/>'

    alg = "ALGORITHM REQ\n"
    if temps:
        alg += "VAR_TEMP\n" + "".join(
            f"  {n} : {('ARRAY[' + a + '] OF ' + ty) if a else ty}{(' := ' + i) if i else ''};\n" for n, ty, a, i in temps) + "END_VAR\n"
    alg += body + "\nEND_ALGORITHM"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<FBType Name="{fb_name}" Comment="iec61131-conformance">
  <Identification Standard="61499-2"/>
  <VersionInfo Version="1.0" Author="harness" Date="2026-01-01"/>
  <InterfaceList>
    <EventInputs>
      <Event Name="REQ" Type="Event">
{"".join(f'        <With Var="{d[0]}"/>' + chr(10) for d in ins)}      </Event>
    </EventInputs>
    <EventOutputs>
      <Event Name="CNF" Type="Event">
{"".join(f'        <With Var="{d[0]}"/>' + chr(10) for d in outs)}      </Event>
    </EventOutputs>
    <InputVars>
{chr(10).join(var(d) for d in ins)}
    </InputVars>
    <OutputVars>
{chr(10).join(var(d) for d in outs)}
    </OutputVars>
  </InterfaceList>
  <BasicFB>
    <InternalVars>
{chr(10).join(var(d) for d in internals)}
    </InternalVars>
    <ECC>
      <ECState Name="START" x="0" y="0"/>
      <ECState Name="RUN" x="400" y="0">
        <ECAction Algorithm="REQ" Output="CNF"/>
      </ECState>
      <ECTransition Source="START" Destination="RUN" Condition="REQ" x="200" y="0"/>
      <ECTransition Source="RUN" Destination="START" Condition="1" x="200" y="100"/>
    </ECC>
    <Algorithm Name="REQ">
      <ST><![CDATA[{alg}]]></ST>
    </Algorithm>
  </BasicFB>
</FBType>
"""


PROJECT = """<?xml version="1.0" encoding="UTF-8"?>
<projectDescription>
\t<name>{name}</name>
\t<comment></comment>
\t<projects></projects>
\t<buildSpec>
\t\t<buildCommand>
\t\t\t<name>org.eclipse.xtext.ui.shared.xtextBuilder</name>
\t\t\t<arguments></arguments>
\t\t</buildCommand>
\t</buildSpec>
\t<natures>
\t\t<nature>org.eclipse.fordiac.ide.systemmanagement.FordiacNature</nature>
\t\t<nature>org.eclipse.xtext.ui.shared.xtextNature</nature>
\t</natures>
</projectDescription>
"""


def ide_command(opts):
    """The IDE is run through the Equinox launcher jar with a JVM rather
    than through its native launcher: on an export error the native
    launcher pops a modal "Error - See the log file" dialog and never
    returns. --ide is the IDE's install directory (the .app on macOS)."""
    ide = Path(opts.ide)
    eclipse = ide / "Contents" / "Eclipse" if (ide / "Contents" / "Eclipse").is_dir() else ide
    jars = sorted((eclipse / "plugins").glob("org.eclipse.equinox.launcher_*.jar"))
    if not jars:
        raise SystemExit(f"no org.eclipse.equinox.launcher_*.jar under {eclipse / 'plugins'}")
    java = opts.java
    if not java:
        bundled = sorted((eclipse / "plugins").glob("org.eclipse.justj.openjdk*/jre/bin/java"))
        java = str(bundled[0]) if bundled else "java"
    cmd = [java]
    if sys.platform == "darwin":
        cmd.append("-XstartOnFirstThread")
    return cmd + ["-jar", str(jars[-1]), "-nosplash", "-consoleLog", "-application", "org.eclipse.ant.core.antRunner"]


def run_ide(opts, work, build_xml):
    ws = work / "workspace"
    shutil.rmtree(ws, ignore_errors=True)
    r = subprocess.run(ide_command(opts) + ["-data", str(ws), "-buildfile", str(build_xml)],
                       capture_output=True, text=True, timeout=900)
    return r.stdout + "\n" + "\n".join(l for l in r.stderr.splitlines() if "Caused by" in l or "Exception" in l and "spifly" not in l)


def build_xml(work, projects, task):
    lines = ['<project name="export" default="export">', '  <target name="export">']
    for name in projects:
        lines.append(f'    <fordiac.importProject projectPath="{work / "proj" / name}"/>')
        lines.append(f'    <fordiac.exportProjectFBs projectName="{name}" exportDirectory="{work / "exported" / name}"/>')
    lines += ["  </target>", "</project>", ""]
    bx = work / "export.xml"
    bx.write_text("\n".join(lines))
    return bx


def export_all(opts, work, projects):
    """projects: name -> {file name: text}. Each becomes a 4diac project, exported
    into work/exported/<name>. Returns name -> error text for the failures."""
    for name, files in projects.items():
        d = work / "proj" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / ".project").write_text(PROJECT.format(name=name))
        for fn, text in files.items():
            (d / fn).write_text(text)

    def done(name):
        return (work / "exported" / name / "src" / f"{name}_fbt.cpp").exists()

    run_ide(opts, work, build_xml(work, projects, None))
    errors = {}
    for name in [n for n in projects if not done(n)]:
        # one failing export aborts the Ant target: export the rest one by one
        log = run_ide(opts, work, build_xml(work, [name], None))
        if not done(name):
            msgs = [x.strip() for x in log.splitlines() if x.strip() and "BUILD" not in x and "Buildfile" not in x
                    and "log4j" not in x and "NLS" not in x and "Total time" not in x and "importProject" not in x
                    and "export:" != x.strip() and "!SESSION" not in x and "eclipse.buildId" not in x
                    and not x.startswith("java.") and "BootLoader" not in x and "arguments:" not in x
                    and not x.strip().startswith("at ") and "!ENTRY" not in x and "!STACK" not in x
                    and "!MESSAGE Application error" not in x]
            errors[name] = "\n".join(msgs[:12]) or "export produced no C++"
    return errors


def cpp_value(ty, value: Value):
    cls, prim = SCALAR[ty]
    if ty == "BOOL":
        return f"CIEC_BOOL({'true' if value.v else 'false'})"
    if ty == "TIME":
        return f"mk_time({value.v}LL)"
    if ty in HEX_WIDTH:
        return f"{cls}(static_cast<{prim}>(0x{value.v:X}u))"
    if ty in REAL_FMT:
        t = value.text
        if t in ("inf", "-inf", "nan"):
            lim = f"std::numeric_limits<{prim}>::"
            expr = {"inf": lim + "infinity()", "-inf": "-" + lim + "infinity()", "nan": lim + "quiet_NaN()"}[t]
        else:
            expr = f"static_cast<{prim}>({t})"
        return f"{cls}({expr})"
    return f"{cls}(static_cast<{prim}>({value.v}))"


def cpp_print(name, ty, expr):
    if ty == "BOOL":
        return f'printf(" {name}=%s", static_cast<bool>({expr}) ? "TRUE" : "FALSE");'
    if ty == "TIME":
        return f'printf(" {name}=T#%lldms", (long long)({expr}).getInMilliSeconds());'
    if ty in HEX_WIDTH:
        return f'printf(" {name}=16#%0{HEX_WIDTH[ty]}llX", (unsigned long long)static_cast<{SCALAR[ty][1]}>({expr}));'
    if ty in REAL_FMT:
        return f'printf(" {name}={REAL_FMT[ty]}", (double)static_cast<{SCALAR[ty][1]}>({expr}));'
    if ty == "STRING":
        return (f'{{ const std::string &s = ({expr}).getStorage(); printf(" {name}=#"); '
                f'for (unsigned char c : s) printf("%02X", c); }}')
    return f'printf(" {name}=%lld", (long long)static_cast<{SCALAR[ty][1]}>({expr}));'


DRIVER = r'''
#include "forte/%(fb)s_fbt.h"
#include "forte/fbcontainer.h"
#include "forte/datatypes/forte_bool.h"
#include "forte/datatypes/forte_int.h"
#include "forte/datatypes/forte_dint.h"
#include "forte/datatypes/forte_uint.h"
#include "forte/datatypes/forte_byte.h"
#include "forte/datatypes/forte_word.h"
#include "forte/datatypes/forte_dword.h"
#include "forte/datatypes/forte_real.h"
#include "forte/datatypes/forte_lreal.h"
#include "forte/datatypes/forte_time.h"
#include "forte/datatypes/forte_string.h"
#include <cstdio>
#include <limits>
#include <string>

using namespace forte;
using namespace forte::literals;

namespace {
class Container final : public CFBContainer {
 public:
  Container() : CFBContainer({}, *this) {}
  CResource *getResource() override { return nullptr; }
  const CResource *getResource() const override { return nullptr; }
  CDevice *getDevice() override { return nullptr; }
  const CDevice *getDevice() const override { return nullptr; }
};
CIEC_TIME mk_time(long long ms) { CIEC_TIME t; t.setFromMilliSeconds(ms); return t; }
}  // namespace

int main() {
  Container cont;
  FORTE_%(fb)s fb("fb"_STRID, cont);
  fb.initialize();
%(inputs)s
%(cycles)s
  return 0;
}
'''


def driver(fb, sections, trace):
    ins = [d for k, ds in sections if k == "VAR_INPUT" for d in ds]
    outs = [d for k, ds in sections if k == "VAR_OUTPUT" for d in ds]
    types = {n: ty for k, ds in sections for n, ty, _, _ in ds}
    for n, ty, array, _ in ins + outs:
        if array:
            raise Unsupported(f"array interface variable {n}")
    lines = []
    for n, ty, _, init in ins:
        v = None
        if init:
            try:
                v = Value.parse(init.upper() if ty in ("BOOL",) else init)
            except ValueError:
                v = None
        lines.append(f"  {SCALAR[ty][0]} in_{n}{' = ' + cpp_value(ty, v) if v else ''};")
    cycles = []
    for rec in trace.records:
        for n, v in rec.inputs:
            cycles.append(f"  in_{n} = {cpp_value(types[n], v)};")
        args = ", ".join([f"in_{n}" for n, *_ in ins] + [f"fb.var_{n}" for n, *_ in outs])
        cycles.append(f"  fb.evt_REQ({args});")
        cycles.append(f'  printf("{rec.cycle} =>");')
        for n in trace.outputs:
            cycles.append("  " + cpp_print(n, types[n], f"fb.var_{n}"))
        cycles.append('  printf("\\n");')
    return DRIVER % {"fb": fb, "inputs": "\n".join(lines), "cycles": "\n".join(cycles)}


def compile_driver(opts, work, fb):
    src = opts.forte_src
    bld = opts.forte_build
    exp = work / "exported" / fb
    cmd = ["c++", "-std=gnu++20", "-O1", "-fno-rtti", "-fno-exceptions", "-DFORTE_LOGERROR", "-w",
           "-I", str(exp / "include"), "-I", f"{src}/core/include", "-I", f"{bld}/core/include",
           "-I", f"{src}/core/arch/common/include", "-I", f"{src}/core/arch/posix/include",
           str(work / f"{fb}_driver.cpp"), str(exp / "src" / f"{fb}_fbt.cpp")] + \
          [str(f) for f in sorted((exp / "src").glob("*_fct.cpp"))] + \
          [str(f) for f in sorted((exp / "src").glob("*_dtp.cpp"))] + [
           "-L", bld, "-L", f"{bld}/core", "-L", f"{bld}/modules/IEC61131-3",
           "-lforte", "-lforte-core", "-lforte-iec61131-3",
           f"-Wl,-rpath,{bld}", f"-Wl,-rpath,{bld}/core", f"-Wl,-rpath,{bld}/modules/IEC61131-3",
           "-o", str(work / f"{fb}_driver")]
    return subprocess.run(cmd, capture_output=True, text=True)


def compare(trace, types, actual_lines):
    problems, recorded = [], []
    by_cycle = {int(l.split()[0]): l for l in actual_lines if l.strip()}
    for rec in trace.records:
        got = by_cycle.get(rec.cycle)
        inp = "".join(f" {n}={v}" for n, v in rec.inputs)
        if got is None:
            problems.append(f"cycle {rec.cycle}: no output (program crashed?)")
            break
        rhs = got.split("=>", 1)[1].strip()
        recorded.append(f"{rec.cycle}{inp} => {canonical_actual(rhs, types)}")
        if rec.expected == "trap":
            problems.append(f"cycle {rec.cycle} (trace line {rec.line}): expected a trap, got {rhs}")
            continue
        actual = dict(tok.split("=", 1) for tok in rhs.split())
        for name, value in rec.expected:
            if value.kind == "any":
                continue
            if not value.matches(actual.get(name), types[name]):
                problems.append(f"cycle {rec.cycle} (trace line {rec.line}): {name} expected {value}, got "
                                f"{canonical_actual(f'{name}={actual.get(name)}', types).split('=', 1)[1]}")
    return problems, recorded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ide", required=True, help="the 4diac IDE install directory (4diac-ide.app on macOS, the unpacked tar.gz on Linux)")
    ap.add_argument("--java", help="JVM to run the IDE with (default: the IDE's bundled JRE, else java on PATH)")
    ap.add_argument("--forte-src", required=True, help="4diac-forte source checkout")
    ap.add_argument("--forte-build", required=True, help="its CMake build directory (shared libraries)")
    ap.add_argument("--record", action="store_true", help="print what the program produced, in .trace record syntax")
    ap.add_argument("--keep", action="store_true", help="keep the temporary directory")
    ap.add_argument("paths", nargs="+")
    opts = ap.parse_args()

    tests = []
    for p in opts.paths:
        p = Path(p)
        tests += sorted(p.rglob("*.st")) if p.is_dir() else [p]

    work = Path(tempfile.mkdtemp(prefix="4diac-"))
    prepared = {}   # st -> ("ok", fb, sections, trace) or ("err", verdict, problems, recorded)
    projects = {}   # fb -> {file name: text}
    for st in tests:
        trace = parse_trace(st.with_suffix(".trace").read_text())
        try:
            st_text = st.read_text()
            functions = parse_functions(st_text)
            user_types = parse_types(st_text)
            name, sections, body = parse_program(st_text, user_types)
            if trace.program and trace.program.lower() != name.lower():
                raise Unsupported(f"trace program {trace.program} is not the PROGRAM {name}")
            types = {n: ty for k, ds in sections for n, ty, _, _ in ds}
            for n in trace.inputs + trace.outputs:
                if n not in types:
                    raise Unsupported(f"variable {n} not declared")
                if types[n] == "STRING" and n in trace.inputs:
                    raise Unsupported("STRING inputs are not supported (SPEC.md)")
                if types[n] not in SCALAR or SCALAR[types[n]][1] is None:
                    raise Unsupported(f"variable {n}: {types[n]} has no trace value syntax")
            fb = "FB_" + re.sub(r"[^A-Za-z0-9]", "_", str(st.with_suffix("")).replace("/", "_"))[-40:].upper()
            projects[fb] = {f"{fb}.fbt": fbt(fb, sections, body)}
            for fname, (rtype, ins, outs, text) in functions.items():
                projects[fb][f"{fname}.fct"] = fct(fname, rtype, ins, outs, text)
            for tname, xml in user_types.items():
                projects[fb][f"{tname}.dtp"] = xml
            prepared[st] = ("ok", fb, sections, trace)
        except Unsupported as e:
            prepared[st] = ("err", "ERROR", [str(e)], [])

    errors = export_all(opts, work, projects) if projects else {}

    counts = {"PASS": 0, "FAIL": 0, "SAME": 0, "DIFFERS": 0, "ERROR": 0}
    for st in tests:
        item = prepared[st]
        if item[0] == "err":
            _, verdict, problems, recorded = item
        else:
            _, fb, sections, trace = item
            types = {n: ty for k, ds in sections for n, ty, _, _ in ds}
            try:
                if fb in errors:
                    verdict = "FAIL" if trace.status == Status.CONFORMANT else "DIFFERS"
                    problems, recorded = ["4diac IDE failed to export the FB:\n" + errors[fb]], []
                else:
                    (work / f"{fb}_driver.cpp").write_text(driver(fb, sections, trace))
                    r = compile_driver(opts, work, fb)
                    if r.returncode != 0:
                        verdict, problems, recorded = "ERROR", ["c++ failed:\n" + r.stderr[:3000]], []
                    else:
                        r = subprocess.run([str(work / f"{fb}_driver")], capture_output=True, text=True, timeout=60)
                        problems, recorded = compare(trace, types, r.stdout.splitlines())
                        if trace.status == Status.CONFORMANT:
                            verdict = "PASS" if not problems else "FAIL"
                        else:
                            verdict = "SAME" if not problems else "DIFFERS"
            except Unsupported as e:
                verdict, problems, recorded = "ERROR", [str(e)], []
            except Exception as e:  # noqa: BLE001
                verdict, problems, recorded = "ERROR", [repr(e)], []
        counts[verdict] += 1
        if opts.record:
            print(f"### {st}")
            for l in recorded:
                print(l)
        print(f"{verdict:8}{st}")
        for p in problems:
            print("        " + p.replace("\n", "\n        "))
    if not opts.keep:
        shutil.rmtree(work, ignore_errors=True)
    else:
        print(f"kept {work}")
    print(f"\n{len(tests)} tests: {counts['PASS']} pass, {counts['FAIL']} fail, {counts['SAME']} same, "
          f"{counts['DIFFERS']} differs, {counts['ERROR']} error")
    return 0 if counts["FAIL"] == 0 and counts["ERROR"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
