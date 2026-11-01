# Differential run: IronPLC vs matiec vs RuSTy (and Beremiz)

Date: 2026-10-31. Same 18 `.st` + `.trace` pairs, three runtimes.

## Runtimes actually run

| runtime | version | how it was driven |
|---|---|---|
| IronPLC | commit `5ea0610`, workspace 0.251.0, `ironplcc compile` + `ironplc_vm` crate | `harness/ironplc` (Rust): `write_variable_raw` per cycle, `run_round(uptime_us)` with simulated time |
| OpenPLC's matiec | OpenPLC_v3 commit `b5d4135`, `utils/matiec_src` (an older matiec snapshot), its `iec2c` and `lib` | `harness/matiec` with `--iec2c`/`--matiec-lib` pointing at the fork |
| STruC++ | Autonomy-Logic/STruCpp commit `72dfcb8` (v0.7.0), the ST to C++14 compiler of OpenPLC Runtime v4, built from source | `harness/strucpp` (Python): generated C++ driver, `IECVar::set/get`, `__CURRENT_TIME_NS` set per step |
| matiec (iec2c) | commit `3a41303` (2026-09-22), built from source with `./configure && make` after `apt-get install flex` | `harness/matiec/run.py`: `iec2c -I lib prog.st` on the test plus a generated `CONFIGURATION` (one task, `INTERVAL := T#<period>ms`), a generated C driver sets `__CURRENT_TIME` and the `RES0__INST0.<VAR>.value` fields, calls `config_run__(tick)` once per record |
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

| test | IronPLC | matiec | OpenPLC's matiec | STruC++ | RuSTy | note |
|---|---|---|---|---|---|---|
| timers/ton | PASS | PASS | PASS | PASS | **FAIL** (cycle 4) | RuSTy raises Q one cycle late: Q = (elapsed > PT), not >= (other runtimes #1) |
| timers/tof | **FAIL** (cycle 0) | PASS | PASS | PASS | **FAIL** (cycles 5, 12) | IronPLC starts an off-delay at power-up with IN never TRUE (findings #1); RuSTy drops Q one cycle late (other runtimes #1) |
| timers/tp | **FAIL** (cycles 5, 10-18) | PASS | PASS | PASS | **FAIL** (cycles 4-8, 16) | IronPLC retriggers while IN stays TRUE, and keeps ET = PT after the pulse with IN FALSE (findings #2, #3); RuSTy's pulse is one cycle long and, after a pulse that ended with IN already FALSE, the block is dead until IN goes TRUE then FALSE again (other runtimes #2) |
| edge/r_trig | PASS | PASS | PASS | PASS | PASS | |
| edge/f_trig | PASS | **FAIL** (cycle 0) | PASS | PASS | PASS | matiec's F_TRIG has `M` initialised FALSE (ed.2 FDIS wording) so it reports a falling edge on the first evaluation with CLK = FALSE; the trace assumes ed.3's `M := TRUE` (findings #6, flagged as the suite's main uncertainty) |
| edge/sr_rs | PASS | PASS | PASS | PASS | **FAIL** (compile) | RuSTy names the bistable inputs `SET1`/`RESET` and `SET`/`RESET1` instead of the standard `S1`/`R` and `S`/`R1` (ed.3 table 42), so a conformant program does not compile (other runtimes #3) |
| edge/power_on_clk_true | PASS | PASS | PASS | PASS | PASS | R_TRIG fires on a first evaluation with CLK TRUE; F_TRIG's start-up ambiguity does not arise |
| counters/ctu | PASS | **FAIL** (cycle 8) | **FAIL** (cycle 8) | **FAIL** (cycle 8) | PASS | matiec stops counting at CV = PV (`CV < PV`, ed.2 FDIS wording); the trace follows ed.3's `CV < PVmax` and counts to 4 (findings #7) |
| counters/ctd | PASS | **FAIL** (cycle 10) | **FAIL** (cycle 10) | **FAIL** (cycle 10) | PASS | matiec stops counting down at CV = 0 (`CV > 0`, ed.2 FDIS wording); the trace follows ed.3's `CV > PVmin` and counts to -1 (same edition difference as ctu) |
| counters/ctud | PASS | **FAIL** (cycles 18-20) | **FAIL** (cycles 18-20) | **FAIL** (cycles 18-20) | PASS | matiec stops at CV = 0 on the way down (cycle 18), so the later up-count lands on 1 instead of 0 (cycle 20). Priorities (R over LD over counting) and the cancelling of simultaneous edges agree on all runtimes |
| counters/ctd_bounds | **FAIL** (cycles 3-6) | PASS | PASS | PASS | PASS | IronPLC wraps -32768 to 32767 on a CD edge (findings #9, ironplc#2332) |
| counters/ctud_bounds | **FAIL** (cycles 3-8) | PASS | PASS | PASS | PASS | IronPLC wraps 32767 to -32768 on a CU edge (findings #9) |
| control-flow/if_case | PASS | PASS | PASS | PASS | PASS | |
| control-flow/for_exit | PASS | PASS | PASS | PASS | PASS | |
| control-flow/while | PASS | PASS | PASS | PASS | PASS | |
| control-flow/nested_exit | PASS | PASS | PASS | PASS | PASS | |
| control-flow/case_expr | PASS | PASS | PASS | PASS | PASS | |
| pou/function_call | PASS | PASS | PASS | PASS | PASS | |
| pou/fb_two_instances | PASS | PASS | PASS | PASS | PASS | |
| pou/fb_input_retention | PASS | PASS | PASS | PASS | PASS | |
| pou/fb_input_defaults | PASS | PASS | PASS | PASS | PASS | |
| pou/function_var_not_retained | PASS | PASS | PASS | PASS | PASS | |
| pou/fb_var_temp | **FAIL** (compile) | PASS | PASS | **FAIL** (cycles 1-3) | PASS | IronPLC: VAR_TEMP in an FB is P9999 not implemented (findings #10, ironplc#1969) |
| pou/fb_en_eno | **FAIL** (compile) | PASS | PASS | PASS | **FAIL** (compile) | IronPLC: `EN :=` in an FB invocation is a syntax error P0002 (findings #14, ironplc#2549); RuSTy: E048 "Could not resolve reference to EN" (other runtimes #5) |
| ops/precedence | PASS | PASS | PASS | PASS | PASS | |
| ops/std_functions | PASS | PASS | PASS | PASS | PASS | |
| ops/std_functions_ext | **FAIL** (compile) | PASS | PASS | PASS | **FAIL** (compile) | IronPLC: MAX and MIN with three inputs are P4018 (findings #11, ironplc#2548, fix in PR #2551); RuSTy: formal argument names on a standard function (`LIMIT(MN := ..)`) are E048 "Could not resolve reference to MN" (other runtimes #4) |
| ops/conversions | PASS | PASS | PASS | PASS | PASS | |
| ops/time_arith | PASS | **ERROR** (build) | PASS | PASS | PASS | matiec emits `_____time_add`/`_____time_sub` for `+`/`-` on TIME (`print_binary_function` adds `___` to a name that already starts with `__`), a symbol that does not exist, so the program never builds (beremiz/matiec#40, fix in PR #45); with #40 fixed, `T#1h2m3s4ms` is still 1 ns short (beremiz/matiec#44) |
| ops/literals | PASS | PASS | PASS | **FAIL** (compile) | PASS | |
| ops/bit_ops | PASS | PASS | PASS | PASS | PASS | |
| data/array_internal | PASS | PASS | PASS | PASS | PASS | |
| data/array_init | PASS | PASS | PASS | PASS | PASS | |
| data/struct_internal | **FAIL** (compile) | PASS | PASS | PASS | PASS | IronPLC: assigning a structure to a structure-typed field (`r.tl := q`) is P9999 not implemented (findings #13, ironplc#2550) |
| data/enum | PASS | PASS | PASS | PASS | PASS | |
| ops/real_arith | PASS | PASS | PASS | PASS | PASS | binary32 arithmetic within the 1e-6 tolerance of SPEC.md |
| ops/real_functions | PASS | PASS | PASS | PASS | PASS | SQRT ABS EXP LN SIN COS |
| ops/real_power | PASS | PASS | PASS | PASS | PASS | EXPT and ** |
| ops/real_conversions | **FAIL** (cycles 0, 1, 3, 4) | PASS | PASS | PASS | PASS | IronPLC truncates REAL_TO_INT and LREAL_TO_DINT instead of rounding to nearest (findings #16, ironplc#1813) |
| ops/real_compare | PASS | PASS | PASS | PASS | PASS | |
| ops/lreal_precision | PASS | PASS | PASS | PASS | **FAIL** (cycles 0-3, big) | binary64 within 1e-12; RuSTy evaluates the untyped literals of `1.0E15 + 1.0` as REAL before widening, giving 999999986991104 (other runtimes #6) |
| strings/literals_escapes | PASS | PASS | PASS | PASS | PASS | |
| strings/declared_length | PASS | **FAIL** (compile) | **FAIL** (compile) | **FAIL** (compile) | PASS | matiec: a `STRING[n]` variable is parsed but then "not declared in this scope" (stage3 visitors for `single_byte_string_var_declaration_c` are commented out; beremiz/matiec#42) |
| strings/functions | PASS | **FAIL** (cycle 0) | **FAIL** (cycles 0-3) | **ERROR** (build) | PASS | matiec: `REPLACE(IN1, IN2, L, P)` copies only min(LEN(IN2), L) characters of IN2 (`__replace`, `iec_std_functions.h`), so with L = 1 'hYllo' instead of 'hYYllo' (beremiz/matiec#41, fix in PR #46) |
| strings/compare | PASS | PASS | **FAIL** (cycles 0-1) | **ERROR** (build) | PASS | |
| strings/concat_assign | PASS | PASS | PASS | PASS | PASS | |
| config/globals_external | PASS | PASS | PASS | PASS | **ERROR** (configuration) | SPEC version 2; RuSTy's harness does not take configurations (RuSTy compiles one program) |
| config/two_periods | **FAIL** (compile) | PASS | PASS | PASS | **ERROR** (configuration) | IronPLC: one program instance only (findings #18, ironplc#1613) |
| config/priority_order | **FAIL** (compile) | **FAIL** (cycles 0-3) | **FAIL** (cycles 0-3) | **FAIL** (cycles 0-3) | **ERROR** (configuration) | matiec runs the tasks of a resource in declaration order, ignoring PRIORITY (`RES0_run__` in the generated res0.c; beremiz/matiec#43, fix in PR #48), so the reader sees g one step late |
| config/global_exchange | **FAIL** (compile) | PASS | PASS | PASS | **ERROR** (configuration) | |
| config/event_single | **FAIL** (compile) | PASS | PASS | **ERROR** (SINGLE not driven) | **ERROR** (configuration) | IronPLC: P4047 SINGLE not supported (findings #18); matiec: an R_TRIG on the SINGLE input, one run per rising edge |
| undefined/int_overflow | SAME | SAME | SAME | SAME | SAME | all three wrap in two's complement |
| undefined/div_zero | SAME | SAME | **DIFFERS** (cycle 2) | **DIFFERS** (cycle 2) | SAME | IronPLC: VM trap "divide by zero"; matiec and RuSTy: native integer division, the process receives SIGFPE (the drivers report it as `trap`). All stop the scan; none computes `MOD`. matiec's `/` is a bare C division, so on AArch64 it returns 0 instead of trapping (beremiz/matiec#38, fix in PR #47); its `MOD` and `DIV()` are guarded |
| undefined/eval_order | SAME | SAME | SAME | SAME | SAME | all three evaluate the left operand of `-` first |
| undefined/for_bound_modified | SAME | SAME | SAME | SAME | SAME | all three re-read the final value on every iteration |
| undefined/ctu_pv_zero | SAME | **DIFFERS** | **DIFFERS** (cycles 1-3) | **DIFFERS** (cycles 1-3) | SAME | IronPLC counts (CV = 1, 2) with Q always TRUE; matiec never counts because `CV < PV` is false at PV = 0, Q always TRUE. Same Q, different CV |
| undefined/ton_pt_change | SAME | **DIFFERS** | **DIFFERS** (cycles 5-11) | **DIFFERS** (cycles 5-11) | **DIFFERS** | IronPLC and matiec raise Q as soon as PT drops below the elapsed time and keep Q TRUE when PT is later raised; but IronPLC's ET keeps climbing to the new PT (400..800 ms) while matiec freezes ET at the old PT (200 ms) once Q has risen. RuSTy is a third behaviour: Q is recomputed every cycle as elapsed > PT, so raising PT makes Q fall again (cycles 5 to 9) and it rises once more at 800 ms |
| undefined/for_var_after_loop | SAME | SAME | SAME | SAME | SAME | all leave the control variable at the first value that failed the test (n + 1), or at its initial value when the body never ran |
| undefined/timer_pt_zero | SAME | **DIFFERS** (cycle 0) | **DIFFERS** (cycle 0) | **DIFFERS** (cycle 0) | **DIFFERS** (cycle 0) | with PT = 0 IronPLC switches one cycle after the edge, matiec and RuSTy on the edge's cycle; the recorded cycle-0 difference is findings #1 (TOF at power-up), the rest agrees (findings #12) |
| undefined/abs_int_min | SAME | SAME | SAME | SAME | SAME | ABS(-32768) and -(-32768) wrap to -32768 on all |
| undefined/dint_to_int_overflow | SAME | SAME | SAME | SAME | SAME | out-of-range *_TO_* truncate in two's complement on all |
| undefined/array_out_of_bounds | SAME | **DIFFERS** (cycle 2) | **DIFFERS** (cycle 2) | SAME | **DIFFERS** (cycle 2) | IronPLC traps ("array index out of bounds"); matiec and RuSTy have no check and read past the array, both give v=4 (findings #15) |
| undefined/real_div_zero | SAME | SAME | SAME | SAME | SAME | inf, -inf, NaN on all, no trap (findings #17) |
| undefined/real_to_int_ties | SAME | **DIFFERS** (cycles 1, 3) | **DIFFERS** (cycles 1, 3) | **DIFFERS** (cycles 0-4) | **DIFFERS** (all ties) | three behaviours: IronPLC truncates (3.5 -> 3), matiec rounds half to even (3.5 -> 4, ed.2 2.5.1.5.1), RuSTy rounds half away from zero (2.5 -> 3, -2.5 -> -3) |
| undefined/string_truncate | SAME | **DIFFERS** (compile) | **DIFFERS** (compile) | **DIFFERS** (compile) | SAME | IronPLC truncates to the declared length; matiec cannot declare `STRING[n]` (see declared_length) |
| undefined/string_conversions | SAME | SAME | SAME | **DIFFERS** (compile) | SAME | plain decimal, leading minus, on all |
| undefined/tasks_same_priority | **DIFFERS** (compile) | SAME | SAME | SAME | **ERROR** (configuration) | records matiec (IronPLC cannot run two instances): declaration order |

Totals: IronPLC 38/51 conformant pass; matiec 43/51; OpenPLC's matiec fork
44/51 (a different set, see below); STruC++ 41/51; RuSTy 39/51 (the five
`config/` tests are outside RuSTy's harness). No test
other than the six control-flow/POU/R_TRIG ones and the four "all SAME"
corners has the same result on all three runtimes: the three disagree
somewhere on tof, tp, f_trig, sr_rs, ctu, ctd, ctud, ctd_bounds, ctud_bounds,
fb_var_temp, fb_en_eno, struct_internal, std_functions_ext, time_arith,
real_conversions, declared_length, functions, ctu_pv_zero, ton_pt_change,
timer_pt_zero, array_out_of_bounds, real_to_int_ties and string_truncate.

## Where the two runtimes disagree with each other, in one line each

1. **TOF at power-up with IN = FALSE**: IronPLC Q = TRUE for PT; matiec Q = FALSE.
2. **TP with IN held TRUE after the pulse**: IronPLC restarts the pulse every PT (free-running oscillator); matiec waits for a new rising edge.
3. **TP ET after the pulse ends with IN FALSE**: IronPLC holds PT; matiec returns to 0.
4. **F_TRIG first evaluation with CLK FALSE**: matiec Q = TRUE; IronPLC Q = FALSE.
5. **CTU above PV, CTD/CTUD below 0**: IronPLC keeps counting to the INT bounds; matiec saturates at PV and at 0 (hence also no count at PV = 0).
6. **TON ET after PT is raised past a Q that already rose**: IronPLC ET follows elapsed time up to the new PT; matiec holds the old PT.
7. **Counters at the INT bounds**: IronPLC wraps (CTD at -32768 gives 32767, CTUD at 32767 gives -32768); matiec saturates.
8. **`+` and `-` on TIME**: matiec's generated C does not build (`_____time_add`); IronPLC computes them.
9. **Timers with PT = 0**: IronPLC switches one cycle after the input edge, matiec on the edge's own cycle.
10. **`STRING[n]` declarations**: matiec rejects them after parsing ("not declared in this scope", beremiz/matiec#42); IronPLC and RuSTy accept them.
11. **`REPLACE` with L shorter than IN2**: matiec inserts only L characters of IN2 (beremiz/matiec#41); IronPLC inserts all of IN2 as table 34 says.
12. **Task priority**: matiec runs the tasks of a resource in declaration order and ignores PRIORITY (beremiz/matiec#43); IronPLC's VM orders by priority but compiles a single instance, so the comparison is between matiec and the standard's text here.

Items 1, 2, 3 are IronPLC deviations from the standard's timing diagrams
(matiec's `lib/timer.txt` reproduces those diagrams in its comments). Item 5
is matiec following the 2001 FDIS text rather than the published editions.
Item 4 depends on which edition's `F_TRIG` body is taken as reference. Item
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
3. **`F_TRIG` is the ed.3 reading**: `Q := NOT CLK AND M; M := CLK;` with `M`
   initially FALSE, so no falling edge is reported on a first evaluation
   with CLK FALSE; `edge/f_trig` passes here and fails on upstream, whose
   body follows the FDIS 2001 text (`notes/findings.md` #6).
4. **`+` and `-` on TIME build**: `print_binary_function()` has no `___`
   prefix in this snapshot, so beremiz/matiec#40 is a later regression;
   `ops/time_arith` passes on Linux x86-64. On macOS arm64 the same build
   gives `T#1h2m3s4ms` 1 ns short (beremiz/matiec#44): the literal macro
   computes in `long double`, which is 80-bit on x86-64 and plain `double`
   on AArch64, so the truncation only bites there.
5. **No `__POUS_INIT_ONLY__` guard**: `undefined/eval_order` builds with
   clang here (beremiz/matiec#39 is also later).

Shared with upstream: `REPLACE` (#41), `STRING[n]` (#42), task order (#43),
counters saturating at PV / 0, rounding to even, the `/` operator unguarded.

## STruC++ deviations (commit `72dfcb8`, v0.7.0)

The timers, edge detectors and bistables pass every trace, `edge/f_trig`
included (the bundled `iec-standard-fb` library takes the ed.3 reading of
`F_TRIG`); the counters follow the FDIS 2001 bodies (`CV < PV`, `CV > 0`),
as matiec's do. The failures are in the front end and the string codegen:

1. **Typed integer literals are not lexed**: `INT#-5`, `UINT#65535`,
   `DINT#16#7FFF_FFFF` and `DINT#-2147483648` stop the lexer with
   "unexpected character `#`" (`ops/literals`, `undefined/string_conversions`);
   `16#FF`, `2#1010_1010`, `8#17` and `1_000_000` are fine. Related:
   Autonomy-Logic/STruCpp#216 (qualified enum literals).
2. **`STRING[n]` is not parsed**, neither in a `VAR` section nor in a `TYPE`
   (`strings/declared_length`, `undefined/string_truncate`).
3. **String literals reach the C++ as `const char[]`**: `LEN('hello')`,
   `CONCAT('ab', 'cd')` and `e < 'a'` are emitted as `LEN("hello")`,
   `CONCAT("ab", "cd")`, `E < "a"`, which the runtime's `IECString`
   templates do not accept, so g++ fails (`strings/functions`,
   `strings/compare`); the same operations on string variables compile.
4. **`VAR_TEMP` is a member of the function block**, so it keeps its value
   between calls: `t := t + x` accumulates (`pou/fb_var_temp`, 7 where 4 is
   expected); a FUNCTION's `VAR` is a local and is not retained
   (`pou/function_var_not_retained` passes).
5. **Division by zero is defined**: `7 / 0 = 0` and `7 MOD 0 = 7`, no trap
   (`undefined/div_zero`); an array index out of range throws
   `std::out_of_range`, which the harness reports as a trap
   (`undefined/array_out_of_bounds` matches).
6. Real-to-integer ties round away from zero, like RuSTy.
7. **Tasks**: STruC++ compiles the configuration (intervals, priorities) but
   leaves the scheduling to the runtime; its own `--build` loop runs the
   tasks in declaration order and the harness follows that rule, so
   `config/priority_order` fails here by construction and `SINGLE` tasks are
   not driven (`config/event_single`, see STruCpp#201). OpenPLC Runtime v4's
   threaded scheduler is not what this harness exercises.

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

Also observed, not a deviation: `TIME` is 32-bit milliseconds in this
build (so `T#500ms` in a trace is the integer 500 in the generated code),
which is why the driver passes milliseconds rather than nanoseconds.

4. **Formal argument names on standard functions** (PLC-lang/rusty#2035, LIMIT declares MIN/MAX; fix in PR #2038): `LIMIT(MN := b, IN := a, MX := c)` and `SEL(G := g, IN0 := a, IN1 := b)` are rejected (E089 invalid call parameters, E048 could not resolve reference to MN), although table 31 names those parameters and 7.2.3.1 allows formal invocation of any function. The positional forms in `ops/std_functions` compile and pass. (`ops/std_functions_ext`)

5. **EN/ENO on a function block invocation** (PLC-lang/rusty#2036): `c(EN := run_it, inc := inc)` is rejected (E089 invalid call parameters, E048 could not resolve reference to EN), so the implicit EN input of ed.3 6.6.1.7 table 20 is not available on function blocks. (`pou/fb_en_eno`)

6. **Untyped real literals are REAL** (PLC-lang/rusty#2037): in `big := 1.0E15 + 1.0` with `big : LREAL`, the sum is computed in binary32 and then widened, so `big` is 999999986991104 instead of 1000000000000001. ed.3 6.3.2 leaves the type of an untyped literal to its context; an `LREAL#` prefix would avoid it. (`ops/lreal_precision`)
