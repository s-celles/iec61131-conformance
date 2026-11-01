# IEC 61131-3 conformance traces

[![CI](https://github.com/s-celles/iec61131-conformance/actions/workflows/ci.yml/badge.svg)](https://github.com/s-celles/iec61131-conformance/actions/workflows/ci.yml)

An open, runtime-agnostic conformance test suite for IEC 61131-3 Structured
Text runtimes: plain `.st` programs paired with plain-text expected
input/output traces, one record per scan cycle. Dedicated to the public
domain under CC0 1.0 (see `LICENSE`).

Status: 67 tests, run against IronPLC, matiec, OpenPLC's matiec fork, STruC++
(and RuSTy,
see `notes/comparison.md`), with a Lean 4 model of the function block
semantics that the expected traces are proved to follow from.

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
  data/        array_internal array_init        arrays (negative bounds, initialisers)
               struct_internal enum             structures (copy, nesting), enumerations
  strings/     literals_escapes declared_length STRING literals and $ escapes, STRING[n]
               functions compare concat_assign  LEN CONCAT LEFT RIGHT MID INSERT DELETE REPLACE FIND, < =, copies
  config/      globals_external                 VAR_GLOBAL / VAR_EXTERNAL (SPEC version 2: the .st has
               two_periods priority_order       its CONFIGURATION); task intervals, PRIORITY order,
               global_exchange event_single     producer/consumer through a global, SINGLE task
  control-flow/ if_case for_exit while          IF/CASE, FOR+EXIT, WHILE/REPEAT
               nested_exit case_expr            EXIT in nested loops, CASE on an expression
  pou/         function_call fb_two_instances   functions, FB instances
               fb_input_retention fb_input_defaults  FB inputs kept across calls, initial values
               function_var_not_retained fb_var_temp FUNCTION VAR and VAR_TEMP are not retained
               fb_en_eno                        implicit EN/ENO on a function block
  undefined/   int_overflow div_zero eval_order ton_pt_change
               for_bound_modified ctu_pv_zero   corners the standard leaves open
               for_var_after_loop timer_pt_zero
               abs_int_min dint_to_int_overflow
               array_out_of_bounds real_div_zero real_to_int_ties
               string_truncate string_conversions
               tasks_same_priority
harness/
  ironplc/     Rust: drives the ironplc_vm crate with simulated time
  matiec/      Python: iec2c + generated C driver with simulated time (also
               drives the matiec fork bundled in OpenPLC_v3)
  strucpp/     Python: strucpp (ST -> C++) + generated C++ driver with simulated time
  rusty/       Python: plc (RuSTy) + mock-time stdlib + C driver
formal/        Lean 4: executable FB semantics, trace theorems, properties
notes/
  ironplcvm-io.md   how ironplcvm can (and cannot) be driven from outside
  comparison.md     differential results between the runtimes (table generated
                    from evidence/ by harness/summarize.py)
  findings.md       IronPLC behaviours that differ from the standard/others
  evidence/         full harness outputs
```

Each test is `<name>.st` + `<name>.trace`. Fifty-one tests under the first
nine categories are `status: conformant`: their expected values were derived
by hand from the standard's function block bodies and timing diagrams, and
the derivation is written as a comment at the top of each `.trace` file.
The sixteen tests under `undefined/` are `status: implementation-defined`: the
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

To bump a runtime, update its SHA in the workflow `env` and the evidence
file together.

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
twice in a row, SR/RS dominance, CTU reset dominance). The two points where
IEC 61131-3 editions differ (`F_TRIG` initial `M`, `CTU` upper bound) are
parameters of the model, and both readings are proved to give different
traces.

What the proofs do not do: they do not prove the model is the standard. The
standard text is not in this repository; the model transcribes the
derivations written in the `.trace` comments, with the assumptions named
there (`F_TRIG` initial `M := TRUE` per ed.3, discrete-time evaluation at
`t = cycle * period`).

## Writing a new test

1. Write the program with one `PROGRAM`, inputs in `VAR_INPUT`, outputs in
   `VAR_OUTPUT`, no `CONFIGURATION`.
2. Write the trace by hand from the standard. Say in the comment which
   clause, table or figure the expectation comes from, and which behaviour
   you assumed where the text is silent. `?` is allowed for a value the
   text leaves open, and must be justified.
3. Run it on at least two runtimes before calling it conformant. If they
   disagree, the comment should say which one the trace follows and why.
