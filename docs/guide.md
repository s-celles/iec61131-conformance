# Guide

Method, layout, continuous integration, and how to build and run each
runtime. The short overview is the [README](../README.md); the results are
browsable at https://s-celles.github.io/iec61131-conformance/. Paths below
are relative to the repository root.

## Method, and what the results do and do not mean

- This is an individual, non-commercial project. It is not produced,
  endorsed or certified by IEC, PLCopen, any accredited or standards body,
  or the projects whose runtimes it runs. Its aim is to help improve the
  existing open-source implementations by reporting reproducible
  differences.
- The expected values of a `status: conformant` trace come from IEC
  61131-3 (edition 2, 2003, and edition 3, 2013: the function block bodies
  and timing diagrams of its tables, the formulas of its standard functions,
  the semantics clauses of ST) as an AI assistant (the commits say
  `Assisted-by: AI`) knows it. Each `.trace` states the derivation and
  the clause, table or figure it cites. The author has no copy of the
  standard, so neither the derivations nor the citations are checked
  against its text: a clause or table number, or the reading itself, may be
  wrong. Where the derivation finds a value left to the implementer (the
  counters' limits PVmin and PVmax, NOTE under ed.3 table 46) the trace does
  not check it. Readings have already been wrong: `F_TRIG` at start-up and
  the counters' limits were corrected on a second reading
  (`notes/findings.md` #6, #7). On 2026-11-18 the edition 2 citations and
  the five traces most runtimes fail were checked against the text of
  IEC 61131-3:2003, which corrected the citations of 22 traces and found one trace,
  `pou/fb_en_eno`, asserting an optional feature as implicit
  (`notes/trace-audit-2026-11-18.md`); edition 3 citations are unchecked.
- The Lean 4 model encodes the same reading, so its proofs show that the
  traces follow from that reading, not that the reading is the standard's.
- A runtime that fails a trace is therefore a claim to check against the
  standard, not a verdict. If you have the text and read a clause
  differently, open an issue citing it.
- `status: implementation-defined` traces record what one runtime (IronPLC)
  does on a corner the standard leaves open. They carry no normative weight;
  `SAME`/`DIFFERS` only says whether another runtime made the same choice.
- The results are for the runtime commits pinned in `.github/workflows/ci.yml`
  and say nothing about later versions. They are not a ranking: the
  runtimes target different editions and scopes, and some failures are
  missing features rather than wrong answers (the notes distinguish them).
- The harnesses are simulated-clock drivers written here, not the projects'
  own tooling. A result marked `ERROR` is a limit of the harness or of the
  build, not of the runtime; a `FAIL` on a construct the harness cannot
  express would be an error in this suite, and is what the notes are for.
- `tools/fuzz` generates programs whose expected trace comes from a small
  reference evaluator rather than from the text; those traces are never
  committed. A divergence found there becomes a test only after a hand
  derivation like the others.

## Layout

```
SPEC.md                   the .trace format (header + one record per cycle)
conformance/
  timers/      ton tof tp                        TON, TOF, TP
  edge/        r_trig f_trig sr_rs              edge detectors and bistables
               power_on_clk_true                 ... started with CLK TRUE
  counters/    ctu ctd ctud                     CTU, CTD, CTUD
               ctd_bounds ctud_bounds           ... at the INT bounds
  ops/         precedence std_functions         operators, ABS MIN MAX LIMIT SEL MUX
               std_functions_ext conversions    extensible/formal calls, *_TO_*
               time_arith literals bit_ops      TIME + - < =, literals, SHL SHR ROL ROR AND OR XOR NOT
               real_arith real_functions        REAL + - * /, SQRT ABS EXP LN SIN COS
               real_power real_conversions      EXPT and **, INT/DINT/UINT <-> REAL/LREAL
               real_compare lreal_precision     comparisons, binary64 at full precision
               date_time trunc                  DATE/TOD/DT arithmetic and conversions, TRUNC
               limit_inverted std_functions_expr LIMIT with MN > MX, MUX/SEL/NOT on expressions (from tools/fuzz)
               bit_literals bit_expr_operands   16# literals as BYTE/WORD, NOT/SHL/ROL on expressions (from tools/fuzz)
               shl_width                        SHL truncates to the width of its input (from tools/fuzz)
               time_mul time_functions          TIME * INT with large products, MIN/MAX/LIMIT/SEL/MUX/LT on TIME (from tools/fuzz)
               mux_types                        MUX on UINT, BYTE, WORD, BOOL, TIME
               minmax_ext_expr                  three-input MIN/MAX with expressions in each position (from tools/fuzz)
               div_call_divisor                 / and MOD with a VAR_IN_OUT call as divisor (from the review of beremiz/matiec#47)
               std_formal_order                 LIMIT SEL MUX called formally, arguments in another order (from tools/fuzz)
               mux_nested_selector time_literal_ms  MUX with a MUX call as selector, duration literals with ms (from tools/fuzz)
               not_compare                      NOT on BYTE/WORD inside = and <> (from tools/fuzz)
  data/        array_internal array_init        arrays (negative bounds, initialisers)
               struct_internal enum             structures (copy, nesting), enumerations
               array_2d array_of_struct         2-D array, array of a named array type, array of structures
               defaults                         default initial values of every type
               struct_init struct_element_copy  member initial values and partial initialisers, copies to/from elements (from tools/fuzz)
  strings/     literals_escapes declared_length STRING literals and $ escapes, STRING[n]
               functions compare concat_assign  LEN CONCAT LEFT RIGHT MID INSERT DELETE REPLACE FIND, < =, copies
               compare_le_ge len_int            <= >= between STRING variables, LEN as an INT (from tools/fuzz)
               insert_positions find_int        INSERT after position P, FIND as a signed INT
               concat_ext min_max_limit         extensible CONCAT, MIN/MAX/LIMIT on STRING variables
               compare_prefix                   = <> between a STRING and its prefix (from tools/fuzz)
  config/      globals_external                 VAR_GLOBAL / VAR_EXTERNAL (SPEC version 2: the .st has
               two_periods priority_order       its CONFIGURATION); task intervals, PRIORITY order,
               global_exchange event_single     producer/consumer through a global, SINGLE task
  control-flow/ if_case for_exit while          IF/CASE, FOR+EXIT, WHILE/REPEAT
               nested_exit case_expr            EXIT in nested loops, CASE on an expression
               return continue for_step         RETURN, CONTINUE (ed.3), FOR BY -n and empty ranges
  pou/         function_call fb_two_instances   functions, FB instances
               fb_input_retention fb_input_defaults  FB inputs kept across calls, initial values
               function_var_not_retained fb_var_temp FUNCTION VAR and VAR_TEMP are not retained
               fb_en_eno                        implicit EN/ENO on a function block
               fb_in_out function_var_output    VAR_IN_OUT (FB and function), function VAR_OUTPUT (=>)
               function_input_default fb_method omitted function inputs, METHOD (ed.3)
               inout_call_in_std_arg            a VAR_IN_OUT/VAR_OUTPUT call as argument of ABS MIN SEL MUX (from tools/fuzz)
               inout_array_element              an array element as a function's VAR_IN_OUT / VAR_OUTPUT (from tools/fuzz)
               output_array_element
               inout_struct_field               a structure member (also of an element) as VAR_IN_OUT / VAR_OUTPUT (from tools/fuzz)
               output_struct_field
  undefined/   int_overflow div_zero eval_order ton_pt_change
               for_bound_modified ctu_pv_zero   corners the standard leaves open
               for_var_after_loop timer_pt_zero
               abs_int_min dint_to_int_overflow
               array_out_of_bounds real_div_zero real_to_int_ties
               string_truncate string_conversions
               tasks_same_priority short_circuit
               subrange_out_of_range
harness/
  ironplc/     Rust: drives the ironplc_vm crate with simulated time
  matiec/      Python: iec2c + generated C driver with simulated time (also
               drives the matiec fork bundled in OpenPLC_v3)
  strucpp/     Python: strucpp (ST -> C++) + generated C++ driver with simulated time
  rk/          Rust: rk compile -> core.wasm, hosted on wasmtime with a simulated
               clock, variables by name through rk's debug_format crate
  4diac/       Python: PROGRAM -> 61499 basic FB (.fbt), 4diac IDE headless export
               to C++ (forte_ng), generated driver against libforte (no clock)
  rusty/       Python: plc (RuSTy) + mock-time stdlib + C driver
  trust/       Python: truST's conformance_driver (native build through truST's
               test harness, simulated time), fed one record per line
formal/        Lean 4: executable FB semantics, trace theorems, properties
tools/fuzz/    differential fuzzing: random well-defined programs + driver (not CI)
tools/site/    generator and build script of the project site (GitHub Pages)
tools/monitor/ rules from the ed.2 text for the standard blocks, checked on traces and evidence
site/          Hugo configuration, layouts and style of the site (theme Hextra)
notes/
  ironplcvm-io.md   how ironplcvm can (and cannot) be driven from outside
  comparison.md     differential results between the runtimes (table generated
                    from evidence/ by harness/summarize.py)
  findings.md       IronPLC behaviours that differ from the standard/others
  evidence/         full harness outputs
```

Each test is `<name>.st` + `<name>.trace`. Ninety-one tests under the first
nine categories are `status: conformant`: their expected values were derived
from the standard's function block bodies, timing diagrams and formulas as
the AI assistant knows them (see the method above), and the derivation is
written as a comment at the top of each `.trace` file.
The eighteen tests under `undefined/` are `status: implementation-defined`: the
trace records what IronPLC actually does, and the comment states what the
standard says or leaves open; a mismatch on another runtime is a documented
difference, not a failure.

Scope: BOOL, INT, DINT, UINT, TIME, BYTE, WORD, DWORD, REAL, LREAL at the
program interface, STRING as an output (arrays, structures and enumerations
inside the program); one program on one cyclic task, or (SPEC version 2,
`config/`) a CONFIGURATION with several tasks and program instances; no
located variables.

## Continuous integration

`.github/workflows/ci.yml` runs on every push and pull request:

- `formal`: checks `Traces.lean` is up to date with the `.trace` files, then
  `lake build` (the proofs are the only hard gate: a `.trace` that no longer
  follows from the model fails the build).
- `ironplc`, `matiec`, `openplc` (the matiec fork in OpenPLC_v3), `strucpp`
  (STruC++, built from source with Node 22): build the runtime at the commit
  recorded in
  `notes/evidence/COMMANDS.md`, run the suite with `--record`, and diff the
  output against `notes/evidence/<runtime>-run.txt`. The runtimes are known
  to fail some conformant tests (`notes/findings.md`), so the harness exit
  status is not the gate; what must not change silently is the recorded
  result. If a change to a test or harness alters it, regenerate the
  evidence file in the same commit and run `python3 -I harness/summarize.py`
  to refresh the results table of `notes/comparison.md` (checked by CI).
- `rusty`: same, on pull requests, weekly and on `workflow_dispatch` (needs
  LLVM 21 and a full RuSTy build; skipped on plain pushes to `main`).
- `rk`: rk built from source at `RK_SHA` (cached), the wasmtime host in
  `harness/rk`.
- `fourdiac`: the 4diac IDE 3.3.0 Linux package and FORTE 3.3.0 built as
  shared libraries, both cached; the IDE runs under `xvfb-run`.
- `trust`: truST's `conformance_driver` and its native toolchain folder built
  from source at `TRUST_SHA` (cached), with the Rust toolchain its
  `rust-toolchain.toml` pins.

To bump a runtime, update its SHA in the workflow `env` and the evidence
file together.

## Project site

https://s-celles.github.io/iec61131-conformance/ shows the same data as the
repository: the results table, the findings (one page each, in a
filterable table), one page per test (program, expected
trace, and what each pinned runtime recorded), the deviations of each
runtime, the upstream issues the notes cite, and the documents (this guide,
`SPEC.md`, the fuzz reports, the changelog), and a History page charting the
suite's size, each runtime's share of conformant tests passed and the
upstream issues cited, from the git history of `notes/comparison.md` (the
Site workflow checks out the full history for it). It also serves `llms.txt`
and `llms-full.txt`. The state of the cited upstream issues comes from
`notes/upstream-status.tsv`, a dated snapshot that
`python3 -I tools/site/upstream_status.py` refreshes (it needs `gh`); the
build itself does not go online.

The pages are not stored in the repository. `tools/site/sitegen.py` derives
them on every build from `conformance/`, `notes/` and the CI pins, and
`.github/workflows/site.yml` builds them with Hugo (Extended, version pinned
in `site/hugo-version`, theme Hextra as a Hugo module, hence Go) and deploys
them to GitHub Pages from `main`. To build locally, outside the repository:

```sh
tools/site/install_hugo.sh ~/.local/hugo           # checksum-pinned Hugo
python3 -I tools/site/test_sitegen.py               # generator checks
tools/site/build.sh /tmp/iec-site ~/.local/hugo/hugo
python3 -m http.server -d /tmp/iec-site/public      # the base URL is the Pages one;
                                                    # set HUGO_BASEURL=http://localhost:8000/ to browse locally
```

The site follows the shared structure of
[s-celles/site-kit](https://github.com/s-celles/site-kit) (its `SPEC.md`),
imported as a Hugo module before Hextra and pinned in `site/go.mod`: the
badges, stat tiles, page head and footer, styles and the `tables.js` and
`viz.js` scripts come from it. The badge tones (one per status word) and the
footer line are set under `params.siteKit` in `site/hugo.yaml`; the menu and
the other declarations the checks read are in `site-kit.json`. The Site
workflow runs site-kit's `check_site.py` on the built site and builds it a
second time to check, with `compare_builds.py`, that both builds are
identical. Locally, with a clone of site-kit next to the repository:

```sh
python3 -I ../site-kit/tools/check_site.py --site /tmp/iec-site/public --config site-kit.json --hugo site/hugo.yaml --repo .
```

The menu has eight entries; the Tests and Runtimes sections are reached from
Docs, the home page tiles and the results table.

## Building the runtimes on NixOS

`shell.nix` provides the toolchains of CI's ubuntu-24.04 job: gcc 13 (gcc 14
turns the implicit declarations of matiec's call wrappers into errors,
`notes/comparison.md` matiec item 13), flex, bison, autotools, Node 22,
rustup (rk's `rust-toolchain.toml` selects its Rust) and xvfb-run. Inside
`nix-shell`, the build commands of `notes/evidence/COMMANDS.md` apply
unchanged. On 2026-11-16 this reproduced every verdict of the IronPLC,
matiec, OpenPLC, STruC++ and rk evidence; only the linker's path in
link errors differs.

## Running against IronPLC

The harness links the `ironplc_vm` crate directly because the `ironplcvm`
command line has no way to inject inputs or simulate time
(`notes/ironplcvm-io.md`). It expects an IronPLC checkout, built, reachable
through a symlink `ironplc-src` at the suite root:

```sh
git clone https://github.com/ironplc/ironplc
(cd ironplc/compiler && cargo build --release --bin ironplcc --bin ironplcvm)
ln -s $PWD/ironplc iec61131-conformance/ironplc-src
cd iec61131-conformance
(cd harness/ironplc && cargo build --release)
./harness/ironplc/target/release/iec61131-conformance-ironplc \
    --ironplcc ironplc-src/compiler/target/release/ironplcc conformance
```

`--record` prints what the VM produced in `.trace` record syntax (that is how
the `undefined/` traces were written). Exit status 1 if any conformant test
fails, so the command is CI-ready.

## Running against matiec

```sh
git clone https://github.com/beremiz/matiec && (cd matiec && ./configure && make)
python3 -I harness/matiec/run.py --iec2c matiec/iec2c --matiec-lib matiec/lib conformance
```

## Running against OpenPLC's matiec fork

OpenPLC_v3 bundles its own, older, matiec (`utils/matiec_src`). The same
harness drives it; only the paths change:

```sh
git clone --depth 1 https://github.com/thiagoralves/OpenPLC_v3 openplc
(cd openplc/utils/matiec_src && autoreconf -i && ./configure && make)
python3 -I harness/matiec/run.py --iec2c openplc/utils/matiec_src/iec2c \
    --matiec-lib openplc/utils/matiec_src/lib conformance
```

## Running against STruC++

STruC++ (Autonomy-Logic/STruCpp, the ST to C++ compiler of OpenPLC Runtime
v4) is a TypeScript program with a header-only C++14 runtime:

```sh
git clone https://github.com/Autonomy-Logic/STruCpp strucpp
(cd strucpp && npm ci --ignore-scripts && npx tsc && node scripts/rebuild-libs.mjs)
python3 -I harness/strucpp/run.py --strucpp "node strucpp/dist/node/cli.js" \
    --runtime-include strucpp/src/runtime/include conformance
```

The harness drives the compiled programs with its own driver; for a
`CONFIGURATION` it runs the periodic tasks the way STruC++'s own REPL loop
does (declaration order, priority ignored) and does not drive `SINGLE` tasks.

## Running against RuSTy

See `harness/rusty/README.md`.

## Running against rk

rk (github.com/adclz/rk) compiles Structured Text to WebAssembly and ships
no runtime; the harness is the host.

```sh
git clone https://github.com/adclz/rk scratch/rk
(cd scratch/rk && git checkout 20761dd && cargo build --release -p rk)
(cd harness/rk && cargo build --release)
./harness/rk/target/release/iec61131-conformance-rk --rk scratch/rk/target/release/rk conformance
```

Each test becomes an rk workspace; the harness prepends one line of `USING`
for rk's `Std.*` namespaces and appends a one-task CONFIGURATION to a bare
PROGRAM (see `notes/comparison.md`, rk section).

## Running against truST

See `harness/trust/README.md`.

## Running against 4diac

Needs the 4diac IDE (3.3.0; the `.app` on macOS or the unpacked
`.tar.gz` on Linux — its bundled JRE is used) and FORTE 3.3.0 built as a
shared library:

```sh
git clone -b 3.3.0 https://github.com/eclipse-4diac/4diac-forte scratch/4diac-forte
cmake -S scratch/4diac-forte -B scratch/4diac-forte/build -DFORTE_ARCHITECTURE=Posix \
    -DFORTE_BUILD_EXECUTABLE=OFF -DBUILD_SHARED_LIBS=ON -DCMAKE_BUILD_TYPE=Release \
    -DFORTE_MODULE_IEC61131=ON -DFORTE_MODULE_CONVERT=ON -DFORTE_MODULE_UTILS=ON \
    -DFORTE_COM_ETH=OFF -DFORTE_COM_FBDK=OFF -DFORTE_COM_LOCAL=ON
cmake --build scratch/4diac-forte/build -j8
python3 -I harness/4diac/run.py --ide /path/to/4diac-ide.app \
    --forte-src scratch/4diac-forte --forte-build scratch/4diac-forte/build conformance
```

The IDE is launched once (all tests as projects of one workspace, one Ant
export), then once more per FB it refused, so a full run takes a few
minutes. Only PROGRAM-only tests over elementary types and FUNCTIONs are in
scope; the rest is reported as `ERROR` with the reason.

## Checking the formal model

```sh
cd formal && lake build          # Lean 4, no Mathlib needed
python3 -I formal/gen_traces.py  # regenerate Traces.lean after editing a .trace
```

`formal/Conformance/Semantics.lean` is an executable model of TON, TOF, TP,
R_TRIG, F_TRIG, SR, RS, CTU, CTD and CTUD as one-cycle state machines, and of
a configuration's task scheduler (periodic and SINGLE tasks run in priority
order, declaration order on ties) applied to the `config/` tests.
`formal/Conformance/Proofs.lean` proves, by evaluation, that each
`status: conformant` trace of those blocks is exactly the model's output,
and proves general properties (TON Q implies ET = PT, TOF never pulses at
power-up, TP never retriggers while IN stays TRUE, edge detectors never fire
twice in a row, SR/RS dominance, CTU reset dominance). Two readings are
parameters of the model, and both are proved to give different traces:
the counters' limits (the INT range, or PV and 0; ed.3 table 46 leaves them to the implementer) and `F_TRIG`'s initial
`M` (the standard's FALSE, per ed.3 table 45, versus the TRUE some runtimes
use).

What the proofs do not do: they do not prove the model is the standard. The
standard text is not in this repository; the model transcribes the
derivations written in the `.trace` comments, with the assumptions named
there (`F_TRIG` initial `M` FALSE per ed.3 table 45, discrete-time evaluation
at `t = cycle * period`).

## Writing a new test

1. Write the program with one `PROGRAM`, inputs in `VAR_INPUT`, outputs in
   `VAR_OUTPUT`, no `CONFIGURATION`.
2. Derive the trace from the standard. Say in the comment which
   clause, table or figure the expectation comes from, and which behaviour
   you assumed where the text is silent. `?` is allowed for a value the
   text leaves open, and must be justified.
3. Run it on at least two runtimes before calling it conformant. If they
   disagree, the comment should say which one the trace follows and why.
4. Add a sheet to `notes/verification.md`: the claim in your own words,
   where to look, a closed question. Until a sheet is answered, the trace
   comment says "verification pending" with the sheet's number.

### Verification sheets

`notes/verification.md` holds one sheet per claim, written without the
text of the standard: the claim, where to look, a closed question. Anyone
with a licensed copy can answer a sheet, in an issue or a pull request,
with a verdict and a clause or table number, without quoting the text. A
verdict then changes the trace: "checked against ed.N, clause" in its
comment, a corrected value, or `status: implementation-defined` where the
standard leaves the value open. No sheet has been answered yet.

## Adding a runtime

A harness is a program that, for each test, compiles the `.st`, then for
each record of the `.trace` writes the inputs, runs exactly one cycle at
the simulated time `cycle * period_ms` (the runtime's clock must be
replaceable: timers read it), reads the outputs and compares them with the
expected values under the rules of `SPEC.md` (REAL tolerance, STRING
escapes, `trap`). The four harnesses here (`harness/`, Rust and Python)
are the models; `harness/strucpp/run.py` is the shortest. To fit the rest
of the repository, a harness should:

- print one verdict line per test, `PASS`/`FAIL` for `conformant` traces
  and `SAME`/`DIFFERS` for `implementation-defined` ones, `ERROR` when the
  test could not be run, followed by detail lines of the form
  `cycle N (trace line L): name expected X, got Y` (or the compiler's
  output), and a final `N tests: ...` summary: `harness/summarize.py`
  reads exactly that;
- offer `--record`, which prints the actual outputs in trace syntax so a
  new `implementation-defined` trace can be filled;
- be driven by a CI job that builds the runtime at a pinned commit, runs
  the suite through `.github/scripts/check-evidence.sh` and uploads the
  output; the recorded output goes to `notes/evidence/<runtime>-run.txt`
  (from Linux, since C runtimes differ by platform), the commands to
  `notes/evidence/COMMANDS.md`, a column to `harness/summarize.py`'s
  `RUNTIMES`, and a section of deviations to `notes/comparison.md`.

## Property monitors

The expected traces were written by an AI assistant, so they are checked
against a second oracle that does not depend on them. `tools/monitor`
holds rules read off the text of IEC 61131-3 edition 2, one per sentence
or table:

- R_TRIG, F_TRIG: the bodies of table 35, with `M` starting FALSE, so
  F_TRIG reports an edge on a first evaluation with CLK FALSE;
- SR, RS: the bodies of table 34;
- CTU, CTD, CTUD: the bodies of table 36, with CU and CD edge-triggered;
  PVmin and PVmax are implementation-dependent, so a count may also stop at
  PV (0 for CTD) or at the bound of INT, but it may not wrap;
- TON, TOF, TP: the timing diagrams of table 38, as rules on Q and ET per
  scan. The one instant the TP diagram leaves open, ET on the cycle a pulse
  ends with IN already FALSE, accepts 0 or PT.

They run, cycle by cycle, on the expected trace of every test that drives
one of these blocks (`monitor.BINDINGS`) and on every runtime's recorded
output in `notes/evidence/`:

```sh
python3 -I tools/monitor/test_monitor.py     # the rules on hand-made sequences
python3 -I tools/monitor/monitor.py --check  # exit 1 if an expected trace violates a rule
```

CI runs both in the `formal` job. A runtime that violates a rule deviates
from the text whatever the trace says; the site lists the result under
"Properties" on each such test page. On 2026-11-18 every expected trace
satisfied every rule, and each runtime violation was a deviation already in
the notes (F_TRIG on four runtimes, IronPLC's counter wrap, TOF at power-up
and TP retrigger, RuSTy's late timers).

## Differential fuzzing

`tools/fuzz/gen.py` generates small, well-defined ST programs (profile
`core`: INT and BOOL; profile `time`: also TIME; profile `wide`: also DINT,
UINT, BYTE and WORD with the conversions, bit-string operators and shifts;
profile `calls`: user FUNCTIONs with VAR_IN_OUT and VAR_OUTPUT and a function
block instance used inside expressions, and formal calls of the standard
functions in any argument order, keeping each expression independent of
evaluation order and short-circuiting; profile `strings`: STRING variables
and literals with the table 34 functions (including CONCAT with two to four
inputs) and the comparisons, every L and P
in range; profile `arrays`: one- and two-dimensional INT arrays with
non-zero lower bounds and an initialiser, read and written with computed
subscripts, also inside FOR loops (an execution that reaches a subscript
outside its subrange is discarded); profile `structs`: a structured type
with a field initial value, structured variables (one with a partial
initialiser) and an array of structures, fields read and written, whole
structures assigned (copied); profiles `array_calls` and `struct_calls`:
array elements and fields also as VAR_IN_OUT and VAR_OUTPUT arguments;
IF/CASE/FOR; the
operators and standard functions whose meaning the standard fixes
completely) with the expected trace from a reference evaluator; `tools/fuzz/run.py` runs them through the local harnesses and
prints the divergences, keeping the programs for reduction. `--exclude`
leaves out constructs with known upstream issues so that new ones show.
This is a search tool, not part of the suite or of CI.

Run `python3 -I tools/fuzz/test_gen.py` to check the string, array and structure evaluator against
table examples and its range guards. The search campaign and reduced cases
of 2026-11-07, 2026-11-15 and 2026-11-16 are recorded in `notes/fuzz-*.md`; local upstream bug
drafts are in `upstream-bugs.md`.

## Citing

`CITATION.cff` gives the citation metadata (CC0; archive and DOI through
Zenodo once a release is tagged).
