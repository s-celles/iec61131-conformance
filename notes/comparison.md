# Differential run: IronPLC vs matiec vs RuSTy (and Beremiz)

Date: 2026-10-31. Same 18 `.st` + `.trace` pairs, three runtimes.

## Runtimes actually run

| runtime | version | how it was driven |
|---|---|---|
| IronPLC | commit `5ea0610`, workspace 0.251.0, `ironplcc compile` + `ironplc_vm` crate | `harness/ironplc` (Rust): `write_variable_raw` per cycle, `run_round(uptime_us)` with simulated time |
| OpenPLC's matiec | OpenPLC_v3 commit `b5d4135`, `utils/matiec_src` (an older matiec snapshot), its `iec2c` and `lib` | `harness/matiec` with `--iec2c`/`--matiec-lib` pointing at the fork |
| STruC++ | Autonomy-Logic/STruCpp commit `72dfcb8` (v0.7.0), the ST to C++14 compiler of OpenPLC Runtime v4, built from source | `harness/strucpp` (Python): generated C++ driver, `IECVar::set/get`, `__CURRENT_TIME_NS` set per step |
| matiec (iec2c) | commit `3a41303` (2026-09-22), built from source with `./configure && make` after `apt-get install flex` | `harness/matiec/run.py`: `iec2c -I lib prog.st` on the test plus a generated `CONFIGURATION` (one task, `INTERVAL := T#<period>ms`), a generated C driver sets `__CURRENT_TIME` and the `RES0__INST0.<VAR>.value` fields, calls `config_run__(tick)` once per record |
| 4diac | Eclipse 4diac IDE 3.3.0 (its Structured Text compiler, run headless through the `fordiac.*` Ant tasks) and FORTE 3.3.0 built as a shared library with CMake | `harness/4diac` (Python): each PROGRAM rewritten as a basic function block (`.fbt`, inputs/outputs/internals, the body as the algorithm of the state entered on `REQ`), FUNCTIONs as `.fct`, exported to C++ by the IDE, a generated driver fires `REQ` once per record against libforte; no clock (nothing in its scope reads one) |
| rk | adclz/rk commit `20761dd` (2026-10-30), Rust (Salsa, HIR/MIR), compiles a workspace to one WebAssembly core module; built from source with `cargo build --release -p rk` | `harness/rk` (Rust): writes an rk workspace (`USING` lines for the `Std.*` namespaces prepended, a one-task CONFIGURATION appended to a bare PROGRAM), runs `rk compile`, hosts `core.wasm` on wasmtime 45 (the version `rk test` uses) with a simulated WASI monotonic clock, runs the program bodies in `rk.schedule` order, variables by name through rk's `debug_format` crate |
| RuSTy (plc) | commit `e911ee5` (2026-10-30), built with LLVM 21 from apt.llvm.org (`LLVM_SYS_211_PREFIX`, `LLVM_CONFIG`); stdlib built with `--features mock_time` | `harness/rusty/run.py`: the program is renamed `conf_prog`, ST accessor functions are appended, `plc -c` with the stdlib `.st` declarations as `-i` includes, a C driver calls `__mock_time_set_ns(cycle * period)` then the accessors. Note: in this build `TIME` is a 32-bit millisecond count (`ET` is `i32` in the IR) |

Commands (from the suite root, `ironplc-src` symlink pointing at the IronPLC checkout):

```sh
cd harness/ironplc && cargo build --release && cd ../..
./harness/ironplc/target/release/iec61131-conformance-ironplc \
    --ironplcc ironplc-src/compiler/target/release/ironplcc --record conformance
python3 -I harness/matiec/run.py --iec2c /path/to/matiec/iec2c \
    --matiec-lib /path/to/matiec/lib --record conformance
python3 -I harness/rusty/run.py --plc /path/to/rusty/target/release/plc \
    --rusty-src /path/to/rusty --record conformance
```

Full outputs: `notes/evidence/ironplc-run.txt`, `notes/evidence/matiec-run.txt`,
`notes/evidence/rusty-run.txt`.

## Beremiz: not run, and why

The Beremiz repository (`github.com/beremiz/beremiz`, cloned) does have a
command-line entry point, `Beremiz_cli.py` (`build`, `transfer`, `run`,
with a `fake_wx` shim so wxPython is not needed to build). It was not used
for the differential run for three reasons:

1. its input is a Beremiz project directory (`plc.xml`, PLCopen XML), not a
   bare `.st` file; Beremiz generates the ST itself from the XML, so a
   PLCopen wrapper around each test would have been needed;
2. its compiler for the ST part is matiec's `iec2c`, the exact binary already
   run above, with Beremiz's own standard library (`NativeLib`) added; the
   function block semantics exercised here (`timer.txt`, `counter.txt`,
   `edge_detection.txt`, `bistable.txt` in `matiec/lib`) are matiec's;
3. its runtime (`targets/plc_main_head.c`) reads `__CURRENT_TIME` from the
   wall clock through `PLC_GetTime` and runs the task loop in real time;
   there is no simulated-time entry point, so a per-cycle trace could not be
   reproduced deterministically without patching its runtime.

So "matiec" below is, for the tested semantics, also what Beremiz executes.
A Beremiz run with a PLCopen wrapper and a patched `PLC_GetTime` is the
obvious next step and would only add coverage of Beremiz's task loop.

## Results

Legend: PASS/FAIL for `status: conformant` traces; SAME/DIFFERS for
`status: implementation-defined` traces, which record IronPLC's behaviour.
The table and the totals are generated from `notes/evidence/*-run.txt` by
`python3 -I harness/summarize.py` (the parenthesis gives the mismatching
cycles, or the stage that failed); only the `note` column is written by
hand. CI checks the table is in sync with the evidence.

<!-- results:begin -->

| test | IronPLC | matiec | OpenPLC's matiec | STruC++ | RuSTy | 4diac | rk | note |
|---|---|---|---|---|---|---|---|---|
| timers/ton | PASS | PASS | PASS | PASS | **FAIL** (cycle 4) | **ERROR** (see evidence) | PASS | RuSTy raises Q one cycle late: Q = (elapsed > PT), not >= (other runtimes #1) |
| timers/tof | **FAIL** (cycle 0) | PASS | PASS | PASS | **FAIL** (cycles 5, 12) | **ERROR** (see evidence) | PASS | IronPLC starts an off-delay at power-up with IN never TRUE (findings #1); RuSTy drops Q one cycle late (other runtimes #1) |
| timers/tp | **FAIL** (cycles 5, 10-18) | PASS | PASS | PASS | **FAIL** (cycles 4-8, 16) | **ERROR** (see evidence) | PASS | IronPLC retriggers while IN stays TRUE, and keeps ET = PT after the pulse with IN FALSE (findings #2, #3); RuSTy's pulse is one cycle long and, after a pulse that ended with IN already FALSE, the block is dead until IN goes TRUE then FALSE again (other runtimes #2) |
| edge/r_trig | PASS | PASS | PASS | PASS | PASS | **ERROR** (see evidence) | PASS |  |
| edge/f_trig | PASS | **FAIL** (cycle 0) | PASS | PASS | PASS | **ERROR** (see evidence) | **FAIL** (cycle 0) | ed.3 table 45 declares `VAR M : BOOL;` (FALSE) and its NOTE gives Q = TRUE on a first execution with CLK FALSE (findings #6, corrected 2026-11-02 after adclz/rk#117); runtimes that start M at TRUE report no edge at cycle 0 |
| edge/sr_rs | PASS | PASS | PASS | PASS | **FAIL** (compile) | **ERROR** (see evidence) | PASS | RuSTy names the bistable inputs `SET1`/`RESET` and `SET`/`RESET1` instead of the standard `S1`/`R` and `S`/`R1` (ed.3 table 42), so a conformant program does not compile (other runtimes #3) |
| edge/power_on_clk_true | PASS | PASS | PASS | PASS | PASS | **ERROR** (see evidence) | PASS | R_TRIG fires on a first evaluation with CLK TRUE, as the NOTE under ed.3 table 45 says; F_TRIG reports nothing whatever its initial M |
| counters/ctu | PASS | **FAIL** (cycle 8) | **FAIL** (cycle 8) | **FAIL** (cycle 8) | PASS | **ERROR** (see evidence) | **FAIL** (cycle 8) | CV past PV depends on PVmax, which the NOTE under ed.3 table 46 leaves implementer specific: IronPLC and RuSTy count to 4, the others stop at PV; CV is not checked on that cycle (findings #7) |
| counters/ctd | PASS | **FAIL** (cycle 10) | **FAIL** (cycle 10) | **FAIL** (cycle 10) | PASS | **ERROR** (see evidence) | **FAIL** (cycle 10) | CV below 0 depends on PVmin (implementer specific, NOTE under ed.3 table 46): IronPLC and RuSTy go to -1, the others stop at 0; CV is not checked on that cycle |
| counters/ctud | PASS | **FAIL** (cycles 18-20) | **FAIL** (cycles 18-20) | **FAIL** (cycles 18-20) | PASS | **ERROR** (see evidence) | **FAIL** (cycles 18-20) | as ctd for CV below 0 (PVmin implementer specific, not checked); priorities (R over LD over counting) and the cancelling of simultaneous edges agree on all runtimes |
| counters/ctd_bounds | **FAIL** (cycles 3-6) | PASS | PASS | PASS | PASS | **ERROR** (see evidence) | PASS | IronPLC wraps -32768 to 32767 on a CD edge (findings #9, ironplc#2332) |
| counters/ctud_bounds | **FAIL** (cycles 3-8) | PASS | PASS | PASS | PASS | **ERROR** (see evidence) | PASS | IronPLC wraps 32767 to -32768 on a CU edge (findings #9) |
| control-flow/if_case | PASS | PASS | PASS | PASS | PASS | PASS | PASS |  |
| control-flow/for_exit | PASS | PASS | PASS | PASS | PASS | PASS | **FAIL** (compile) |  |
| control-flow/while | PASS | PASS | PASS | PASS | PASS | PASS | **FAIL** (compile) |  |
| control-flow/nested_exit | PASS | PASS | PASS | PASS | PASS | PASS | PASS |  |
| control-flow/case_expr | PASS | PASS | PASS | PASS | PASS | PASS | PASS |  |
| pou/function_call | PASS | PASS | PASS | PASS | PASS | PASS | **FAIL** (compile) |  |
| pou/fb_two_instances | PASS | PASS | PASS | PASS | PASS | **ERROR** (see evidence) | PASS |  |
| pou/fb_input_retention | PASS | PASS | PASS | PASS | PASS | **ERROR** (see evidence) | PASS |  |
| pou/fb_input_defaults | PASS | PASS | PASS | PASS | PASS | **ERROR** (see evidence) | PASS |  |
| pou/function_var_not_retained | PASS | PASS | PASS | PASS | PASS | PASS | PASS |  |
| pou/fb_var_temp | **FAIL** (compile) | PASS | PASS | **FAIL** (cycles 1-3) | PASS | **ERROR** (see evidence) | PASS | IronPLC: VAR_TEMP in an FB is P9999 not implemented (findings #10, ironplc#1969) |
| pou/fb_en_eno | **FAIL** (compile) | PASS | PASS | PASS | **FAIL** (compile) | **ERROR** (see evidence) | **FAIL** (compile) | IronPLC: `EN :=` in an FB invocation is a syntax error P0002 (findings #14, ironplc#2549); RuSTy: E048 "Could not resolve reference to EN" (other runtimes #5) |
| ops/precedence | PASS | PASS | PASS | PASS | PASS | PASS | PASS |  |
| ops/std_functions | PASS | PASS | PASS | PASS | PASS | **ERROR** (see evidence) | PASS |  |
| ops/std_functions_ext | **FAIL** (compile) | PASS | PASS | PASS | **FAIL** (compile) | **FAIL** (see evidence) | **FAIL** (compile) | IronPLC: MAX and MIN with three inputs are P4018 (findings #11, ironplc#2548, fix in PR #2551); RuSTy: formal argument names on a standard function (`LIMIT(MN := ..)`) are E048 "Could not resolve reference to MN" (other runtimes #4) |
| ops/conversions | PASS | PASS | PASS | PASS | PASS | PASS | **FAIL** (compile) |  |
| ops/time_arith | PASS | **ERROR** (build) | PASS | PASS | PASS | **FAIL** (see evidence) | PASS | matiec emits `_____time_add`/`_____time_sub` for `+`/`-` on TIME (`print_binary_function` adds `___` to a name that already starts with `__`), a symbol that does not exist, so the program never builds (beremiz/matiec#40, fix in PR #45); with #40 fixed, `T#1h2m3s4ms` is still 1 ns short (beremiz/matiec#44) |
| ops/literals | PASS | PASS | PASS | **FAIL** (compile) | PASS | PASS | **FAIL** (compile) |  |
| ops/bit_ops | PASS | PASS | PASS | PASS | PASS | PASS | PASS |  |
| data/array_internal | PASS | PASS | PASS | PASS | PASS | PASS | PASS |  |
| data/array_init | PASS | PASS | PASS | PASS | PASS | PASS | PASS |  |
| data/struct_internal | **FAIL** (compile) | PASS | PASS | PASS | PASS | PASS | PASS | IronPLC: assigning a structure to a structure-typed field (`r.tl := q`) is P9999 not implemented (findings #13, ironplc#2550) |
| data/enum | PASS | PASS | PASS | PASS | PASS | **FAIL** (see evidence) | **FAIL** (compile) | 4diac: the forte_ng exporter rejects enumerated data types (4diac item 10) |
| ops/real_arith | PASS | PASS | PASS | PASS | PASS | PASS | PASS | binary32 arithmetic within the 1e-6 tolerance of SPEC.md |
| ops/real_functions | PASS | PASS | PASS | PASS | PASS | PASS | PASS | SQRT ABS EXP LN SIN COS |
| ops/real_power | PASS | PASS | PASS | PASS | PASS | PASS | PASS | EXPT and ** |
| ops/real_conversions | **FAIL** (cycles 0-1, 3-4) | PASS | PASS | PASS | PASS | PASS | **FAIL** (compile) | IronPLC truncates REAL_TO_INT and LREAL_TO_DINT instead of rounding to nearest (findings #16, ironplc#1813) |
| ops/real_compare | PASS | PASS | PASS | PASS | PASS | PASS | PASS |  |
| ops/lreal_precision | PASS | PASS | PASS | PASS | **FAIL** (cycles 0-3) | PASS | **FAIL** (cycles 0-3) | binary64 within 1e-12; RuSTy evaluates the untyped literals of `1.0E15 + 1.0` as REAL before widening, giving 999999986991104 (other runtimes #6) |
| strings/literals_escapes | PASS | PASS | PASS | PASS | PASS | PASS | **FAIL** (compile) |  |
| strings/declared_length | PASS | **FAIL** (compile) | **FAIL** (compile) | **FAIL** (compile) | PASS | **ERROR** (see evidence) | **FAIL** (compile) | matiec: a `STRING[n]` variable is parsed but then "not declared in this scope" (stage3 visitors for `single_byte_string_var_declaration_c` are commented out; beremiz/matiec#42) |
| strings/functions | PASS | **FAIL** (cycle 0) | **FAIL** (cycles 0-3) | **ERROR** (build) | PASS | **FAIL** (cycle 3) | **FAIL** (compile) | matiec: `REPLACE(IN1, IN2, L, P)` copies only min(LEN(IN2), L) characters of IN2 (`__replace`, `iec_std_functions.h`), so with L = 1 'hYllo' instead of 'hYYllo' (beremiz/matiec#41, fix in PR #46) |
| strings/compare | PASS | PASS | **FAIL** (cycles 0-1) | **ERROR** (build) | PASS | PASS | PASS |  |
| strings/concat_assign | PASS | PASS | PASS | PASS | PASS | PASS | **FAIL** (compile) |  |
| config/globals_external | PASS | PASS | PASS | PASS | **ERROR** (configuration) | **ERROR** (configuration) | **FAIL** (compile) | SPEC version 2; RuSTy's harness does not take configurations (RuSTy compiles one program) |
| config/two_periods | **FAIL** (compile) | PASS | PASS | PASS | **ERROR** (configuration) | **ERROR** (configuration) | PASS | IronPLC: one program instance only (findings #18, ironplc#1613) |
| config/priority_order | **FAIL** (compile) | **FAIL** (cycles 0-3) | **FAIL** (cycles 0-3) | **FAIL** (cycles 0-3) | **ERROR** (configuration) | **ERROR** (configuration) | PASS | matiec runs the tasks of a resource in declaration order, ignoring PRIORITY (`RES0_run__` in the generated res0.c; beremiz/matiec#43, fix in PR #48), so the reader sees g one step late |
| config/global_exchange | **FAIL** (compile) | PASS | PASS | PASS | **ERROR** (configuration) | **ERROR** (configuration) | PASS |  |
| config/event_single | **FAIL** (compile) | PASS | PASS | **ERROR** (SINGLE not driven) | **ERROR** (configuration) | **ERROR** (configuration) | **FAIL** (compile) | IronPLC: P4047 SINGLE not supported (findings #18); matiec: an R_TRIG on the SINGLE input, one run per rising edge |
| undefined/int_overflow | SAME | SAME | SAME | SAME | SAME | SAME | SAME | all three wrap in two's complement |
| undefined/div_zero | SAME | SAME | SAME | SAME | SAME | **DIFFERS** (cycle 2) | SAME | IronPLC: VM trap "divide by zero"; matiec and RuSTy: native integer division, the process receives SIGFPE (the drivers report it as `trap`). All stop the scan; none computes `MOD`. matiec's `/` is a bare C division, so on AArch64 it returns 0 instead of trapping (beremiz/matiec#38, fix in PR #47); its `MOD` and `DIV()` are guarded |
| undefined/eval_order | SAME | SAME | SAME | SAME | SAME | **ERROR** (see evidence) | SAME | all three evaluate the left operand of `-` first |
| undefined/for_bound_modified | SAME | SAME | SAME | SAME | SAME | **DIFFERS** (cycles 0, 2) | **DIFFERS** (cycles 0, 2) | all three re-read the final value on every iteration |
| undefined/ctu_pv_zero | SAME | **DIFFERS** (cycles 1-3) | **DIFFERS** (cycles 1-3) | **DIFFERS** (cycles 1-3) | SAME | **ERROR** (see evidence) | **DIFFERS** (cycles 1-3) | IronPLC counts (CV = 1, 2) with Q always TRUE; matiec never counts because `CV < PV` is false at PV = 0, Q always TRUE. Same Q, different CV |
| undefined/ton_pt_change | SAME | **DIFFERS** (cycles 5-11) | **DIFFERS** (cycles 5-11) | **DIFFERS** (cycles 5-11) | **DIFFERS** (cycles 3, 5-9) | **ERROR** (see evidence) | **DIFFERS** (cycles 5-8) | IronPLC and matiec raise Q as soon as PT drops below the elapsed time and keep Q TRUE when PT is later raised; but IronPLC's ET keeps climbing to the new PT (400..800 ms) while matiec freezes ET at the old PT (200 ms) once Q has risen. RuSTy is a third behaviour: Q is recomputed every cycle as elapsed > PT, so raising PT makes Q fall again (cycles 5 to 9) and it rises once more at 800 ms |
| undefined/for_var_after_loop | SAME | SAME | SAME | SAME | SAME | SAME | SAME | all leave the control variable at the first value that failed the test (n + 1), or at its initial value when the body never ran |
| undefined/timer_pt_zero | SAME | **DIFFERS** (cycle 0) | **DIFFERS** (cycle 0) | **DIFFERS** (cycle 0) | **DIFFERS** (cycle 0) | **ERROR** (see evidence) | **DIFFERS** (cycle 0) | with PT = 0 IronPLC switches one cycle after the edge, matiec and RuSTy on the edge's cycle; the recorded cycle-0 difference is findings #1 (TOF at power-up), the rest agrees (findings #12) |
| undefined/abs_int_min | SAME | SAME | SAME | SAME | SAME | SAME | SAME | ABS(-32768) and -(-32768) wrap to -32768 on all |
| undefined/dint_to_int_overflow | SAME | SAME | SAME | SAME | SAME | SAME | SAME | out-of-range *_TO_* truncate in two's complement on all |
| undefined/array_out_of_bounds | SAME | **DIFFERS** (cycle 2) | **DIFFERS** (cycle 2) | SAME | **DIFFERS** (cycle 2) | **DIFFERS** (see evidence) | SAME | IronPLC traps ("array index out of bounds"); matiec and RuSTy have no check and read past the array, both give v=4 (findings #15) |
| undefined/real_div_zero | SAME | SAME | SAME | SAME | SAME | **DIFFERS** (cycles 1-3) | SAME | inf, -inf, NaN on all, no trap (findings #17) |
| undefined/real_to_int_ties | SAME | **DIFFERS** (cycles 1, 3) | **DIFFERS** (cycles 1, 3) | **DIFFERS** (cycles 0-4) | **DIFFERS** (cycles 0-4) | **DIFFERS** (cycles 1, 3) | **DIFFERS** (cycles 1, 3) | three behaviours: IronPLC truncates (3.5 -> 3), matiec rounds half to even (3.5 -> 4, ed.2 2.5.1.5.1), RuSTy rounds half away from zero (2.5 -> 3, -2.5 -> -3) |
| undefined/string_truncate | SAME | **DIFFERS** (compile) | **DIFFERS** (compile) | **DIFFERS** (compile) | SAME | **ERROR** (see evidence) | **DIFFERS** (compile) | IronPLC truncates to the declared length; matiec cannot declare `STRING[n]` (see declared_length) |
| undefined/string_conversions | SAME | SAME | SAME | **DIFFERS** (compile) | SAME | **DIFFERS** (see evidence) | **DIFFERS** (compile) | plain decimal, leading minus, on all |
| undefined/tasks_same_priority | **DIFFERS** (compile) | SAME | SAME | SAME | **ERROR** (configuration) | **ERROR** (configuration) | SAME | records matiec (IronPLC cannot run two instances): declaration order |
| control-flow/continue | **FAIL** (compile) | PASS | PASS | **FAIL** (compile) | PASS | PASS | PASS | ed.3 CONTINUE: matiec and the fork have it; IronPLC (findings #20) and STruC++ (STruC++ #10) do not parse it |
| control-flow/for_step | PASS | PASS | PASS | PASS | PASS | PASS | PASS | negative BY, overshooting BY, empty range: all agree |
| control-flow/return | PASS | PASS | PASS | PASS | PASS | **ERROR** (see evidence) | PASS | RETURN in an FB and in a function, on all |
| data/array_2d | **FAIL** (compile) | PASS | **FAIL** (compile) | PASS | PASS | **ERROR** (see evidence) | PASS | two-dimensional array and array of a named array type with a nested initialiser: IronPLC rejects the nested initialiser (findings #22), the OpenPLC fork crashes on it (fork #6) |
| data/array_of_struct | **FAIL** (compile) | PASS | **FAIL** (compile) | PASS | PASS | PASS | PASS | structure initialisers inside an array initialiser: IronPLC (findings #22) and the OpenPLC fork (fork #7) reject the syntax |
| data/defaults | PASS | PASS | PASS | **FAIL** (cycles 0-1) | **FAIL** (cycles 0-1) | **ERROR** (see evidence) | **FAIL** (compile) | default initial values: STruC++ (STruC++ #9, STruCpp#260) and RuSTy (RuSTy #7, PLC-lang/rusty#2039) start a subrange at 0 instead of its lower limit; everything else agrees |
| ops/date_time | PASS | **ERROR** (build) | PASS | **FAIL** (compile) | PASS | PASS | **FAIL** (compile) | IronPLC and the OpenPLC fork compute all of table 30; upstream matiec does not build (`_____time_sub`, beremiz/matiec#40); STruC++ types `TOD - TOD` as TOD (STruC++ #8, STruCpp#259) |
| ops/trunc | PASS | PASS | PASS | PASS | PASS | **FAIL** (see evidence) | PASS | TRUNC toward zero on all |
| pou/fb_in_out | **FAIL** (compile) | PASS | PASS | PASS | PASS | **ERROR** (see evidence) | PASS | IronPLC does not lower VAR_IN_OUT of an FB (findings #21); upstream matiec builds the function with VAR_IN_OUT only where an implicit declaration is not an error (matiec #13, beremiz/matiec#49) |
| pou/fb_method | **FAIL** (compile) | **FAIL** (compile) | **FAIL** (compile) | PASS | PASS | **ERROR** (see evidence) | PASS | ed.3 METHOD: STruC++ only; IronPLC (findings #20) and both matiecs are ed.2 |
| pou/function_input_default | **FAIL** (compile) | PASS | PASS | PASS | PASS | **FAIL** (cycles 0-2) | PASS | IronPLC requires every function input (P4018, findings #23, ironplc#2552); the others apply the initial value |
| pou/function_var_output | PASS | PASS | PASS | PASS | PASS | PASS | PASS | function VAR_OUTPUT read with `=>`: all agree; upstream matiec builds it with an implicit-declaration warning (matiec #13) |
| undefined/short_circuit | SAME | **DIFFERS** (cycles 0-2) | **DIFFERS** (cycles 0-2) | SAME | SAME | **ERROR** (see evidence) | SAME | records IronPLC (full evaluation); both matiecs short-circuit (fork #8), STruC++ and RuSTy evaluate fully |
| undefined/subrange_out_of_range | SAME | SAME | SAME | SAME | SAME | **ERROR** (see evidence) | **DIFFERS** (cycle 1) | records IronPLC: stored unchecked; same on all that run it |
| ops/limit_inverted | PASS | **FAIL** (cycles 0-1, 5) | **FAIL** (cycles 0-1, 5) | **FAIL** (cycles 1, 5) | **FAIL** (cycles 1, 5) | **ERROR** (see evidence) | PASS | LIMIT with MN > MX follows MIN(MAX(IN, MN), MX): IronPLC only; matiec (matiec #14, beremiz/matiec#50), its fork (fork #9), STruC++ (STruC++ #13) and RuSTy (RuSTy #8, PLC-lang/rusty#2040) test MN first and return it. Found by tools/fuzz |
| ops/std_functions_expr | PASS | PASS | PASS | **ERROR** (build) | PASS | **ERROR** (see evidence) | PASS | MUX, SEL and NOT on expressions: STruC++ does not compile MUX with expression inputs nor NOT of an AND of comparisons (STruC++ #11, #12, STruCpp#262, #263); the others agree. Found by tools/fuzz |
| ops/bit_expr_operands | PASS | PASS | PASS | PASS | PASS | PASS | PASS | NOT, SHL, ROL, ROR on bit-string expressions: all agree. Found by tools/fuzz |
| ops/bit_literals | **FAIL** (compile) | PASS | PASS | PASS | PASS | PASS | PASS | untyped 16# literals as BYTE/WORD values: IronPLC types them ANY_INT and rejects every use (findings #26, ironplc#2554); the others accept them. Found by tools/fuzz |
| ops/shl_width | **FAIL** (cycles 0-4) | PASS | PASS | PASS | PASS | PASS | PASS | SHL truncates to its input's width: IronPLC shifts in a 32-bit slot and masks only at the store, so SHR/OR of a SHL result sees the lost bits (findings #25, ironplc#2553); the others agree. Found by tools/fuzz |
| ops/time_functions | **FAIL** (compile) | **ERROR** (build) | PASS | PASS | PASS | **ERROR** (see evidence) | **FAIL** (compile) | MIN/MAX/LIMIT/SEL/MUX/LT on TIME: IronPLC rejects MIN, MAX and LIMIT on TIME (findings #27, ironplc#2555); upstream matiec does not build the `a + b` (#40); the fork, STruC++ and RuSTy agree. Found by tools/fuzz |
| ops/time_mul | PASS | **ERROR** (build) | **FAIL** (cycles 0-4) | PASS | PASS | **FAIL** (see evidence) | **FAIL** (compile) | TIME * n with large products: matiec's __time_mul overflows a 32-bit int (matiec #15, beremiz/matiec#51; upstream does not build TIME arithmetic, #40, the fork shows it, fork #10); IronPLC, STruC++ and RuSTy agree. Found by tools/fuzz |
| ops/mux_types | PASS | PASS | PASS | PASS | PASS | **ERROR** (see evidence) | **FAIL** (compile) | MUX on UINT/BYTE/WORD/BOOL/TIME (table 32: ANY): rk has no unsigned or bit-string MUX overload (rk item 9); 4diac has no func_MUX.h (4diac item 3) |

Totals (89 tests, 71 with `status: conformant`): conformant tests passed, IronPLC 49/71; matiec 58/71; OpenPLC's matiec 59/71; STruC++ 56/71; RuSTy 57/71; 4diac 31/71; rk 46/71. 19 of the 89 tests have the same result on all seven runtimes.

<!-- results:end -->

## Where the two runtimes disagree with each other, in one line each

1. **TOF at power-up with IN = FALSE**: IronPLC Q = TRUE for PT; matiec Q = FALSE.
2. **TP with IN held TRUE after the pulse**: IronPLC restarts the pulse every PT (free-running oscillator); matiec waits for a new rising edge.
3. **TP ET after the pulse ends with IN FALSE**: IronPLC holds PT; matiec returns to 0.
4. **F_TRIG first evaluation with CLK FALSE**: matiec Q = TRUE, as ed.3 table 45 and its NOTE say; IronPLC Q = FALSE (its M starts at TRUE).
5. **CTU above PV, CTD/CTUD below 0**: IronPLC keeps counting to the INT bounds; matiec stops at PV and at 0 (hence also no count at PV = 0). Both are permitted: PVmax and PVmin are implementer specific (NOTE under ed.3 table 46).
6. **TON ET after PT is raised past a Q that already rose**: IronPLC ET follows elapsed time up to the new PT; matiec holds the old PT.
7. **Counters at the INT bounds**: IronPLC wraps (CTD at -32768 gives 32767, CTUD at 32767 gives -32768), a defect whatever the limits; matiec stays at the bound.
8. **`+` and `-` on TIME**: matiec's generated C does not build (`_____time_add`); IronPLC computes them.
9. **Timers with PT = 0**: IronPLC switches one cycle after the input edge, matiec on the edge's own cycle.
10. **`STRING[n]` declarations**: matiec rejects them after parsing ("not declared in this scope", beremiz/matiec#42); IronPLC and RuSTy accept them.
11. **`REPLACE` with L shorter than IN2**: matiec inserts only L characters of IN2 (beremiz/matiec#41); IronPLC inserts all of IN2 as table 34 says.
12. **Task priority**: matiec runs the tasks of a resource in declaration order and ignores PRIORITY (beremiz/matiec#43); IronPLC's VM orders by priority but compiles a single instance, so the comparison is between matiec and the standard's text here.
13. **Functions with VAR_OUTPUT or VAR_IN_OUT call an undeclared function** (beremiz/matiec#49): for such a function matiec emits a per-call `static inline` wrapper (`__MAIN_DIVMOD1`) outside the `#ifndef __POUS_INIT_ONLY__` guard, while the function's prototype is inside it; `config.c` includes `POUS.c` with that macro defined, so the wrapper calls `___DIVMOD` before any declaration (`pou/function_var_output`, `pou/fb_in_out` (`SWAP`), `undefined/short_circuit`). With gcc 13 (CI) that is a warning and the three tests run correctly; with clang, or gcc 14 where implicit declarations are errors, the build fails, as with beremiz/matiec#39. The OpenPLC fork has no guard.
14. **`LIMIT` with MN > MX returns MN** (beremiz/matiec#50): matiec's `LIMIT` tests `IN <= MN` first, so `LIMIT(5, 3, 1)` is 5 where the standard's formula `MIN(MAX(IN, MN), MX)` (ed.3 table 32) gives 1; IronPLC follows the formula (`ops/limit_inverted`, found by `tools/fuzz`; the suite's other LIMIT tests keep MN <= MX). The OpenPLC fork (item 9), STruC++ (item 13) and RuSTy (item 8) do the same.
15. **`TIME * n` overflows a 32-bit intermediate** (beremiz/matiec#51): `lib/C/iec_std_lib.h` `__time_mul` computes `(int)((LREAL)IN1.tv_nsec * IN2)`, so once the nanosecond part times the factor exceeds 2^31 (`T#700ms * 4`, `T#999ms * 3`) the product is wrong (`ops/time_mul`: 2147 ms instead of 2800); upstream does not build it (#40) but has the same line, the OpenPLC fork shows it. Found by `tools/fuzz` (profile `time`).

Items 1, 2, 3 are IronPLC deviations from the standard's timing diagrams
(matiec's `lib/timer.txt` reproduces those diagrams in its comments). Item 5
is a choice the standard leaves open (ed.3 table 46, NOTE).
Item 4 is an IronPLC deviation (ed.3 table 45, findings #6). Item
6 is outside what the standard defines.

## OpenPLC's matiec fork (OpenPLC_v3 `b5d4135`, `utils/matiec_src`)

An older matiec snapshot; the same harness drives it. Where it differs from
upstream matiec `3a41303`:

1. **String comparison stops at the shorter length**: `__STR_CMP` is a
   `memcmp` over `min(len1, len2)`, so `'ab' < 'abc'` and `'' < 'a'` are
   FALSE (a prefix compares equal). Upstream compares the lengths after the
   common part. (`strings/compare`)
2. **`FIND` returns `LEN(IN1) + 1` when `IN2` is absent** instead of 0:
   `FIND('hello', 'zz')` is 6. (`strings/functions`)
3. **`F_TRIG` reports no edge on a first evaluation with CLK FALSE**: its body
   is `Q := NOT CLK AND M; M := CLK;` with `M` initially FALSE, equivalent to
   the table 45 body with `M` at TRUE; ed.3 table 45 and its NOTE give
   Q = TRUE there (`edge/f_trig`, `notes/findings.md` #6). Upstream matiec
   has the standard's body.
4. **`+` and `-` on TIME build**: `print_binary_function()` has no `___`
   prefix in this snapshot, so beremiz/matiec#40 is a later regression;
   `ops/time_arith` passes on Linux x86-64. On macOS arm64 the same build
   gives `T#1h2m3s4ms` 1 ns short (beremiz/matiec#44): the literal macro
   computes in `long double`, which is 80-bit on x86-64 and plain `double`
   on AArch64, so the truncation only bites there.
5. **No `__POUS_INIT_ONLY__` guard**: `undefined/eval_order` builds with
   clang here (beremiz/matiec#39 is also later), and so do functions with
   `VAR_OUTPUT` / `VAR_IN_OUT` (upstream item 13).
6. **Nested array initialiser is an internal compiler error**:
   `a : ARRAY[0..1] OF ROW := [[10, 20, 30], [40, 50, 60]]` with
   `ROW : ARRAY[0..2] OF INT` stops `iec2c` with "Internal compiler error
   in file ./generate_c_vardecl.cc at line 249" (`data/array_2d`); without
   the initialiser it compiles, and upstream matiec accepts it.
7. **Structure initialisers inside an array initialiser are rejected**:
   `[(x := 1, y := 10), ...]` gives "Initialization element identifier (x)
   is not declared in referenced structure/FB scope" (`data/array_of_struct`);
   upstream matiec accepts it.
8. **AND / OR short-circuit** (`undefined/short_circuit`, DIFFERS from the
   IronPLC record): the generated C uses `&&` / `||`, so the right operand's
   function is not called when the left one decides; upstream matiec does
   the same.
9. **`LIMIT` with MN > MX returns MN**, as upstream (item 14;
   `ops/limit_inverted`).
10. **`TIME * n` overflows a 32-bit intermediate**, as upstream (item 15;
    `ops/time_mul`: `T#700ms * 4` is 2147 ms).

Shared with upstream: `REPLACE` (#41), `STRING[n]` (#42), task order (#43),
counters stopping at PV / 0 (permitted), rounding to even, the `/` operator unguarded.

## STruC++ deviations (commit `72dfcb8`, v0.7.0)

The timers, `R_TRIG` and the bistables pass every trace; `F_TRIG` starts with
its `M` at TRUE, so it reports no edge on a first evaluation with CLK FALSE
where ed.3 table 45 and its NOTE give one (`edge/f_trig`); the counters
stop at PV and 0, as matiec's do, which the implementer-specific limits of
ed.3 table 46 permit. The failures are in the front end and the string codegen:

1. **A typed literal with a negative value is not lexed** (Autonomy-Logic/STruCpp#255): `INT#-5` and
   `DINT#-2147483648` stop the lexer with "unexpected character `#`"
   (`ops/literals`, `undefined/string_conversions`); the `TypedLiteral` token
   (`src/frontend/lexer.ts:536`) has no sign in its pattern. `UINT#65535`,
   `DINT#16#7FFF_FFFF`, `16#FF`, `2#1010_1010`, `8#17` and `1_000_000` are
   fine. Related: Autonomy-Logic/STruCpp#216 (qualified enum literals).
2. **`STRING[n]` is not parsed** (STruCpp#256), neither in a `VAR` section nor in a `TYPE`
   (`strings/declared_length`, `undefined/string_truncate`).
3. **String literals reach the C++ as `const char[]`** (STruCpp#257): `LEN('hello')`,
   `CONCAT('ab', 'cd')` and `e < 'a'` are emitted as `LEN("hello")`,
   `CONCAT("ab", "cd")`, `E < "a"`, which the runtime's `IECString`
   templates do not accept, so g++ fails (`strings/functions`,
   `strings/compare`); the same operations on string variables compile.
4. **`VAR_TEMP` is a member of the function block** (STruCpp#258), so it keeps its value
   between calls: `t := t + x` accumulates (`pou/fb_var_temp`, 7 where 4 is
   expected); a FUNCTION's `VAR` is a local and is not retained
   (`pou/function_var_not_retained` passes).
5. **Integer division by zero is the bare C++ division**: SIGFPE on x86-64
   (`undefined/div_zero` matches the trap), `7 / 0 = 0` and `7 MOD 0 = 7` on
   AArch64, the same CPU dependence as matiec's `/` (beremiz/matiec#38); an
   array index out of range throws `std::out_of_range`, which the harness
   reports as a trap (`undefined/array_out_of_bounds` matches).
6. Real-to-integer ties round away from zero, like RuSTy.
7. **Tasks**: STruC++ compiles the configuration (intervals, priorities) but
   leaves the scheduling to the runtime; its own `--build` loop runs the
   tasks in declaration order and the harness follows that rule, so
   `config/priority_order` fails here by construction and `SINGLE` tasks are
   not driven (`config/event_single`, see STruCpp#201). OpenPLC Runtime v4's
   threaded scheduler is not what this harness exercises, and it cannot be
   driven by a simulated clock: `core/src/plc_app/plc_state_manager.cpp`
   (autonomy-logic/openplc-runtime `8d69d93`) runs one `SCHED_FIFO` thread
   per task, released by a master-tick dispatcher paced with
   `clock_nanosleep` on `CLOCK_MONOTONIC` at the GCD of the intervals; all
   tasks due at a tick are posted together and the order in which they run
   is the OS scheduler's (IEC priority mapped to FIFO 49..1 by
   `task_policy.h`), so on more than one core they run concurrently and
   `priority_order` has no defined answer. The `SINGLE` parameter does not
   survive compilation at all: `TaskInstance` (`iec_std_lib.hpp`) carries
   `name, interval_ns, priority, programs` and a `SINGLE` task is emitted
   with `interval_ns = 0`, which v4 then schedules at the base tick
   (`ctx->interval_ns = tk.interval_ns > 0 ? ... : base_ns`), i.e. every
   tick regardless of the trigger. Reproducing that rule in the harness
   would only confirm the deviation; the real-time run would add
   non-determinism. Left as a documented limitation.
8. **`TOD - TOD` is typed as `TOD`** (STruCpp#259) instead of `TIME` (ed.3 table 30),
   so `(TOD#12:00:00 + T#90m) - TOD#00:00:00` assigned to a TIME is rejected
   with "Cannot assign TIME_OF_DAY to TIME" (`ops/date_time`); IronPLC and
   the OpenPLC fork compute the test.
9. **A subrange variable starts at 0, not at its lower limit** (STruCpp#260):
   `sm : SMALL` with `SMALL : INT (5..10)` reads 0 (`data/defaults`, 5
   expected per ed.3 6.4.4.4.3; IronPLC and both matiecs give 5). An
   out-of-range assignment is stored unchecked, like the others
   (`undefined/subrange_out_of_range`).
10. **No `CONTINUE`** (STruCpp#261, ed.3 7.3.3.4.2): "Unexpected identifier `CONTINUE`
   after `THEN`" (`control-flow/continue`). `METHOD` is supported
   (`pou/fb_method` passes).
11. **`MUX` with expression inputs does not compile** (STruCpp#262): `MUX(k, a + b, a * 2, MAX(a, b))`
    is emitted as is, and C++ integer promotion makes `A + B` an `int` while
    `MAX(A, B)` is an `IEC_INT`, so the `MUX(IEC_INT k, T in0, T in1, ...)`
    template cannot deduce `T` ("no matching function for call to 'MUX'",
    `ops/std_functions_expr`; `ops/std_functions` with variable inputs
    passes). Found by `tools/fuzz`, where it hit a third of the programs.
12. **`NOT` of an AND/OR/XOR of comparisons does not compile** (STruCpp#263):
    `NOT ((a < b) AND (b < 10))` becomes `NOT((A < B) & (B < 10))`, whose
    operand is an `int` (`bool & bool`), which the `NOT` template refuses;
    `NOT (a = b)` and `NOT (p XOR q)` on BOOL variables compile
    (`ops/std_functions_expr`).
13. **`LIMIT` with MN > MX returns MN** (`IN < MN ? MN : ...`), like matiec
    item 14 (`ops/limit_inverted`); `LIMIT(0, 0, -16)` is -16 here where
    matiec gives 0 (`IN <= MN`).

## 4diac (IDE 3.3.0 and FORTE 3.3.0)

4diac implements IEC 61499, where Structured Text is the language of a
basic function block's algorithms, so only the tests that are one PROGRAM
(plus FUNCTIONs as `.fct`, STRUCT and enumeration TYPEs as `.dtp`) can be
posed to it. The rest is `ERROR` by construction: FUNCTION_BLOCK types,
timers, counters and edge detectors (61499 has no ST FB instances inside
an algorithm; its TON/CTU are event-driven blocks of another kind),
CONFIGURATION, array/subrange TYPE aliases and `STRING[n]` (no `.dtp`
form), `VAR_IN_OUT` on a function. The totals are in the table. What differs:

1. **`DELETE` refuses a range that ends at the last character** (eclipse-4diac/4diac-forte#1133):
   `func_DELETE.h` tests `P + L > LEN(IN)` where the deleted range is
   `P .. P + L - 1`, so `DELETE('hello', 4, 2)` returns `'hello'`
   instead of `'h'` (`strings/functions`).
2. **`func_LIMIT.h` does not include `func_MAX.h` / `func_MIN.h`** (4diac-forte#1134), so an
   algorithm that uses LIMIT without also using MAX or MIN does not compile
   (`ops/limit_inverted`: "use of undeclared identifier 'func_MAX'").
3. **No `func_MUX.h` in FORTE 3.3.0** (4diac-forte#1135) while the IDE 3.3.0 exports
   `#include "forte/iec61131_functions/func_MUX.h"` for `MUX`
   (`ops/std_functions`, `ops/std_functions_expr`, `ops/time_functions`
   do not compile); the IDE's own evaluator has MUX.
4. **Omitted function inputs are 0, not their initial value** (eclipse-4diac/4diac-ide#3130)
   (`pou/function_input_default`: `SCALE(x := x)` with `k : INT := 3`
   computes with `k = 0`); ed.3 6.6.1.7.1 gives the initial value.
   IronPLC rejects the call instead (findings #23); the others apply it.
5. **The formal parameter names of LIMIT and SEL** (4diac-ide#3132) are `min`/`value`/`max`
   and `g`/`in0`/`in1`, not the standard's `MN`/`IN`/`MX` and
   `G`/`IN0`/`IN1` (`ops/std_functions_ext`: "The parameter MN is undefined
   for the callable LIMIT"); the same class as RuSTy #2035.
6. **A duration literal with a fractional unit is not lexed** (4diac-ide#3131): `T#1.5s`
   gives "no viable alternative at input '5s'" (`ops/time_arith`); ed.3
   table 8 allows it.
7. **A variable named `t` cannot be used in an expression** (4diac-ide#3131): the lexer
   takes `t` as the prefix of a `T#` literal ("mismatched input '*'
   expecting '#'", `ops/time_mul`, `ops/trunc`). Likely the same for `d`,
   `dt`, `tod`, `ltime`... — identifiers that equal a literal type prefix.
8. **`TRUNC` exists only in the typed forms** (4diac-ide#3132) `TRUNC_INT`, `TRUNC_DINT`...
   in the IDE ("The callable TRUNC(REAL) is undefined", `ops/trunc`),
   although FORTE ships `func_TRUNC.h`.
9. **No `*_TO_STRING` / `STRING_TO_*` conversions** (4diac-ide#3132): 4diac names them
   `*_AS_STRING` (`undefined/string_conversions`).
10. **Enumerated types cannot be exported to FORTE**: a `.dtp` with an
    `EnumeratedType` stops the forte_ng exporter with "Unknown source type
    EnumeratedType" (`data/enum`); STRUCT data types export and run
    (`data/struct_internal`, `data/array_of_struct` pass). Array aliases,
    subranges and `STRING[n]` have no `.dtp` form at all and stay out of
    scope (`data/array_2d`, `data/defaults`, `undefined/subrange_out_of_range`).
11. Corners the standard leaves open (`undefined/`): integer division by
    zero gives 0 without a trap, real division by zero gives 0 (not inf),
    an index out of bounds crashes the process (no check), a FOR bound is
    evaluated once (3 iterations where IronPLC re-reads it, 50),
    real-to-integer ties round away from zero (as STruC++ and RuSTy).

In CI (`fourdiac` job): the IDE's Linux package and a cached FORTE build,
under `xvfb-run`; the evidence file is that run's output.

## rk (commit `20761dd`)

rk is strict by design (220+ diagnostics, no implicit narrowing) and says
so; several of its refusals are documented choices that differ from the
standard rather than defects. The harness adapts only what a user of rk
would write anyway: `USING Std.Math; USING Std.Strings; ...` on one line in
front of each test (rk keeps the standard functions and blocks in
namespaces; a POU of the program still wins over an imported one), and a
one-task CONFIGURATION after a bare PROGRAM (rk only runs a program a task
runs). Diagnostics' line numbers are therefore one more than in the `.st`.
Task order is rk's own contract: the `rk.schedule` section lists the tasks
"most urgent first" and the host runs the due ones in that order
(`config/priority_order` passes).

Documented choices that make a conformant test fail to compile:

1. **Widening conversions exist only implicitly**: `INT_TO_DINT`,
   `UINT_TO_DINT`, `INT_TO_REAL` ... are not declared (`docs/strict-casts.md`
   lists them as implicit only), while ed.3 table 22 has every `*_TO_**`
   (`ops/conversions`, `ops/real_conversions`, `control-flow/for_exit`,
   `control-flow/while`, `pou/function_call`, `config/globals_external`).
2. **An enumerated value is always qualified**: `Color#Green`; a bare
   `Green` is `E0201` (`docs/enums.md`), where ed.3 6.4.4.2 allows the bare
   name when it is unambiguous (`data/enum`).
3. **`LEN` returns `UDINT`** (`stdlib/Strings.st`), and `LEFT`/`RIGHT`/
   `MID`'s lengths are `UDINT`, with no implicit `UDINT` to `INT`; ed.2
   table 29 and ed.3 table 34 give `LEN` an INT result
   (`strings/functions`, `strings/literals_escapes`, `strings/concat_assign`,
   `strings/declared_length`, `data/defaults`).
4. **`DATE - DATE`, `TOD +/- TIME`, `TIME * INT` are refused** (`E0305`;
   `docs/time-and-dates.md`: "only durations of the same type add and
   subtract"), all in ed.3 table 30 (`ops/date_time`, `ops/time_mul`).
5. **MIN/MAX take two inputs only** (adclz/rk#116; "no overload of 'MAX' takes 3
   parameters"), where table 32 makes them extensible; and `LT`, `GT`, ...
   exist only as operators (`ops/std_functions_ext`, `ops/time_functions`).
6. **No EN/ENO** on a function block call (`pou/fb_en_eno`).
7. **No SINGLE tasks**: "event-driven tasks (SINGLE) are not supported"
   (`E1410`, `config/event_single`).
8. **A negative based literal is a syntax error** (adclz/rk#115): `-16#10` gives
   "unexpected token(s): '# 1 0'" (`ops/literals`); `-(16#10)` is accepted.
   Not documented, and the only lexer defect met.
9. **`MUX` has no overload for unsigned integers, `SINT`, bit strings or
   dates** (adclz/rk#114) (`stdlib/Selection.st`: BOOL, INT, DINT, LINT, REAL, LREAL, TIME,
   STRING), while `SEL` has them all and table 32 declares both on ANY;
   `MUX(k, a, b)` on UINT is `E0809` "ambiguous overloaded call"
   (`ops/mux_types`, found by `tools/fuzz`). The help text of that error
   suggests `INT_TO_DINT(x)`, which rk does not declare (item 1).

Semantic differences in what runs:

10. **The counters stop at PV and 0** (`CV < PV`, `CV > 0`), as matiec and
   STruC++ do: permitted, since the NOTE under ed.3 table 46 leaves PVmax and
   PVmin to the implementer (raised on adclz/rk#117, withdrawn; only
   `undefined/ctu_pv_zero` still differs from the IronPLC record).
11. **`F_TRIG` is the standard's**: rk's body is ed.3 table 45's, with `M`
    initially FALSE and Q = TRUE on a first evaluation with CLK FALSE as the
    table's NOTE says; adclz pointed this out on adclz/rk#117, and the suite's
    `edge/f_trig` trace was corrected (`notes/findings.md` #6).
12. **Untyped real literals are REAL**: `1.0E15 + 1.0` assigned to an LREAL
    is computed in binary32 (`ops/lreal_precision`), as RuSTy (#2037); rk
    documents it (`docs/math-operations.md`: "a literal computes at its own
    type first", write `LREAL#`).
13. Corners the standard leaves open (`undefined/`): a value outside a
    subrange raises a WebAssembly exception (rk's bounds checks; IronPLC
    stores it), real-to-integer ties round away from zero, a FOR bound is
    evaluated once, `TON` holds ET at the old PT when PT is raised after Q,
    a `TOF` with PT = 0 never raises Q, and assigning a literal longer than
    a `STRING[n]` is a compile error (`E0314`) rather than a truncation
    (`undefined/string_truncate`).

Everything else passes: the timers, `SR`/`RS`, structures, arrays
(two-dimensional and of structures), `CONTINUE`, `RETURN`, methods,
`VAR_IN_OUT`, string comparison, `REAL`/`LREAL` functions, bit strings,
configurations with globals and several instances, task priority. Integer
division by zero and an index out of bounds stop the scan as the IronPLC
records do (`undefined/div_zero`, `undefined/array_out_of_bounds`: SAME).

## RuSTy deviations (commit `e911ee5`)

RuSTy is not the subject of this suite, but the runs produced six clear
results, reported upstream to PLC-lang/rusty (#2032 to #2037), each with a reproducer
in `conformance/` and the output in `notes/evidence/rusty-run.txt`:

1. **Timers are one cycle late** (PLC-lang/rusty#2032): `libs/stdlib/src/timers.rs`,
   `is_in_preset_range` tests `elapsed <= PT`, so TON's Q rises, TOF's Q
   falls and TP's pulse ends when the elapsed time *exceeds* PT, one cycle
   after ET has reached PT. The standard's diagrams (and matiec's
   `START_TIME + PT <= CURRENT_TIME`) switch at equality.
2. **TP dies after a pulse that ends with IN already FALSE** (PLC-lang/rusty#2033) (`timers/tp`,
   cycles 6 to 11): `run_tp` only resets the block on a falling edge of IN
   seen *after* the pulse has expired. If IN fell during the pulse, no edge
   is seen afterwards, `is_running` stays TRUE, ET stays at PT, and a later
   rising edge of IN is ignored (`q=FALSE` at cycle 6 where a new pulse is
   due). The block recovers only after IN goes TRUE and FALSE again.
3. **SR/RS input names** (PLC-lang/rusty#2034) are `SET1`/`RESET` and `SET`/`RESET1`
   (`libs/stdlib/iec61131-st/bistable_functionblocks.st`), so programs
   written with the standard's `S1`/`R` and `S`/`R1` (ed.3 table 42) fail to
   compile with `E048 Could not resolve reference to S1`.
7. **A subrange variable starts at 0, not at its lower limit** (PLC-lang/rusty#2039)
   (`data/defaults`, `SMALL : INT (5..10)` reads 0 where ed.3 6.4.4.4.3 gives
   5; IronPLC and both matiecs give 5, STruC++ also 0). Every other lot 4
   test passes on RuSTy, CONTINUE and METHOD included.
8. **`LIMIT` with MN > MX returns MN** (PLC-lang/rusty#2040, `ops/limit_inverted`): the same
   `MN` first order as matiec item 14 and STruC++ item 13, where the
   standard's formula `MIN(MAX(IN, MN), MX)` gives MX.

Also observed, not a deviation: `TIME` is 32-bit milliseconds in this
build (so `T#500ms` in a trace is the integer 500 in the generated code),
which is why the driver passes milliseconds rather than nanoseconds.

4. **Formal argument names on standard functions** (PLC-lang/rusty#2035, LIMIT declares MIN/MAX; fix in PR #2038): `LIMIT(MN := b, IN := a, MX := c)` and `SEL(G := g, IN0 := a, IN1 := b)` are rejected (E089 invalid call parameters, E048 could not resolve reference to MN), although table 31 names those parameters and 7.2.3.1 allows formal invocation of any function. The positional forms in `ops/std_functions` compile and pass. (`ops/std_functions_ext`)

5. **EN/ENO on a function block invocation** (PLC-lang/rusty#2036): `c(EN := run_it, inc := inc)` is rejected (E089 invalid call parameters, E048 could not resolve reference to EN), so the implicit EN input of ed.3 6.6.1.7 table 20 is not available on function blocks. (`pou/fb_en_eno`)

6. **Untyped real literals are REAL** (PLC-lang/rusty#2037): in `big := 1.0E15 + 1.0` with `big : LREAL`, the sum is computed in binary32 and then widened, so `big` is 999999986991104 instead of 1000000000000001. ed.3 6.3.2 leaves the type of an untyped literal to its context; an `LREAL#` prefix would avoid it. (`ops/lreal_precision`)
