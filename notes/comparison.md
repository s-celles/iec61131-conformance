# Differential run: IronPLC vs matiec vs RuSTy (and Beremiz)

Date: 2026-10-31. Same 18 `.st` + `.trace` pairs, three runtimes.

## Runtimes actually run

| runtime | version | how it was driven |
|---|---|---|
| IronPLC | commit `5ea0610`, workspace 0.251.0, `ironplcc compile` + `ironplc_vm` crate | `harness/ironplc` (Rust): `write_variable_raw` per cycle, `run_round(uptime_us)` with simulated time |
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

| test | IronPLC | matiec | RuSTy | note |
|---|---|---|---|---|
| timers/ton | PASS | PASS | **FAIL** (cycle 4) | RuSTy raises Q one cycle late: Q = (elapsed > PT), not >= (other runtimes #1) |
| timers/tof | **FAIL** (cycle 0) | PASS | **FAIL** (cycles 5, 12) | IronPLC starts an off-delay at power-up with IN never TRUE (findings #1); RuSTy drops Q one cycle late (other runtimes #1) |
| timers/tp | **FAIL** (cycles 5, 10-18) | PASS | **FAIL** (cycles 4-8, 16) | IronPLC retriggers while IN stays TRUE, and keeps ET = PT after the pulse with IN FALSE (findings #2, #3); RuSTy's pulse is one cycle long and, after a pulse that ended with IN already FALSE, the block is dead until IN goes TRUE then FALSE again (other runtimes #2) |
| edge/r_trig | PASS | PASS | PASS | |
| edge/f_trig | PASS | **FAIL** (cycle 0) | PASS | matiec's F_TRIG has `M` initialised FALSE (ed.2 FDIS wording) so it reports a falling edge on the first evaluation with CLK = FALSE; the trace assumes ed.3's `M := TRUE` (findings #6, flagged as the suite's main uncertainty) |
| edge/sr_rs | PASS | PASS | **FAIL** (compile) | RuSTy names the bistable inputs `SET1`/`RESET` and `SET`/`RESET1` instead of the standard `S1`/`R` and `S`/`R1` (ed.3 table 42), so a conformant program does not compile (other runtimes #3) |
| counters/ctu | PASS | **FAIL** (cycle 8) | PASS | matiec stops counting at CV = PV (`CV < PV`, ed.2 FDIS wording); the trace follows ed.3's `CV < PVmax` and counts to 4 (findings #7) |
| counters/ctd | PASS | **FAIL** (cycle 10) | PASS | matiec stops counting down at CV = 0 (`CV > 0`, ed.2 FDIS wording); the trace follows ed.3's `CV > PVmin` and counts to -1 (same edition difference as ctu) |
| counters/ctud | PASS | **FAIL** (cycles 18-20) | PASS | matiec stops at CV = 0 on the way down (cycle 18), so the later up-count lands on 1 instead of 0 (cycle 20). Priorities (R over LD over counting) and the cancelling of simultaneous edges agree on all runtimes |
| control-flow/if_case | PASS | PASS | PASS | |
| control-flow/for_exit | PASS | PASS | PASS | |
| control-flow/while | PASS | PASS | PASS | |
| pou/function_call | PASS | PASS | PASS | |
| pou/fb_two_instances | PASS | PASS | PASS | |
| undefined/int_overflow | SAME | SAME | SAME | all three wrap in two's complement |
| undefined/div_zero | SAME | SAME | SAME | IronPLC: VM trap "divide by zero"; matiec and RuSTy: native integer division, the process receives SIGFPE (the drivers report it as `trap`). All stop the scan; none computes `MOD`. matiec's `/` is a bare C division, so on AArch64 it returns 0 instead of trapping (beremiz/matiec#38); its `MOD` and `DIV()` are guarded |
| undefined/eval_order | SAME | SAME | SAME | all three evaluate the left operand of `-` first |
| undefined/for_bound_modified | SAME | SAME | SAME | all three re-read the final value on every iteration |
| undefined/ctu_pv_zero | SAME | **DIFFERS** | SAME | IronPLC counts (CV = 1, 2) with Q always TRUE; matiec never counts because `CV < PV` is false at PV = 0, Q always TRUE. Same Q, different CV |
| undefined/ton_pt_change | SAME | **DIFFERS** | **DIFFERS** | IronPLC and matiec raise Q as soon as PT drops below the elapsed time and keep Q TRUE when PT is later raised; but IronPLC's ET keeps climbing to the new PT (400..800 ms) while matiec freezes ET at the old PT (200 ms) once Q has risen. RuSTy is a third behaviour: Q is recomputed every cycle as elapsed > PT, so raising PT makes Q fall again (cycles 5 to 9) and it rises once more at 800 ms |

Totals: IronPLC 12/14 conformant pass; matiec 10/14; RuSTy 10/14. No test
other than the six control-flow/POU/R_TRIG ones and the four "all SAME"
corners has the same result on all three runtimes: the three disagree
somewhere on tof, tp, f_trig, sr_rs, ctu, ctd, ctud, ctu_pv_zero and
ton_pt_change.

## Where the two runtimes disagree with each other, in one line each

1. **TOF at power-up with IN = FALSE**: IronPLC Q = TRUE for PT; matiec Q = FALSE.
2. **TP with IN held TRUE after the pulse**: IronPLC restarts the pulse every PT (free-running oscillator); matiec waits for a new rising edge.
3. **TP ET after the pulse ends with IN FALSE**: IronPLC holds PT; matiec returns to 0.
4. **F_TRIG first evaluation with CLK FALSE**: matiec Q = TRUE; IronPLC Q = FALSE.
5. **CTU above PV, CTD/CTUD below 0**: IronPLC keeps counting to the INT bounds; matiec saturates at PV and at 0 (hence also no count at PV = 0).
6. **TON ET after PT is raised past a Q that already rose**: IronPLC ET follows elapsed time up to the new PT; matiec holds the old PT.

Items 1, 2, 3 are IronPLC deviations from the standard's timing diagrams
(matiec's `lib/timer.txt` reproduces those diagrams in its comments). Item 5
is matiec following the 2001 FDIS text rather than the published editions.
Item 4 depends on which edition's `F_TRIG` body is taken as reference. Item
6 is outside what the standard defines.

## RuSTy deviations (commit `e911ee5`)

RuSTy is not the subject of this suite, but the run produced three clear
results worth reporting upstream to PLC-lang/rusty, each with a reproducer
in `conformance/` and the output in `notes/evidence/rusty-run.txt`:

1. **Timers are one cycle late**: `libs/stdlib/src/timers.rs`,
   `is_in_preset_range` tests `elapsed <= PT`, so TON's Q rises, TOF's Q
   falls and TP's pulse ends when the elapsed time *exceeds* PT, one cycle
   after ET has reached PT. The standard's diagrams (and matiec's
   `START_TIME + PT <= CURRENT_TIME`) switch at equality.
2. **TP dies after a pulse that ends with IN already FALSE** (`timers/tp`,
   cycles 6 to 11): `run_tp` only resets the block on a falling edge of IN
   seen *after* the pulse has expired. If IN fell during the pulse, no edge
   is seen afterwards, `is_running` stays TRUE, ET stays at PT, and a later
   rising edge of IN is ignored (`q=FALSE` at cycle 6 where a new pulse is
   due). The block recovers only after IN goes TRUE and FALSE again.
3. **SR/RS input names** are `SET1`/`RESET` and `SET`/`RESET1`
   (`libs/stdlib/iec61131-st/bistable_functionblocks.st`), so programs
   written with the standard's `S1`/`R` and `S`/`R1` (ed.3 table 42) fail to
   compile with `E048 Could not resolve reference to S1`.

Also observed, not a deviation: `TIME` is 32-bit milliseconds in this
build (so `T#500ms` in a trace is the integer 500 in the generated code),
which is why the driver passes milliseconds rather than nanoseconds.
