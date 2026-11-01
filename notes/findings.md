# Findings: IronPLC behaviours that differ from the standard or from matiec

IronPLC commit `5ea0610` (0.251.0). Every item has a reproducer in
`conformance/` and the actual output in `notes/evidence/ironplc-run.txt`.
Classification of the two failing conformant tests: both are **IronPLC
behaviours**, not harness or test bugs (the same harness passes the other 10
conformant tests, and the matiec harness passes both tests with the same
trace files, so the trace files are consistent with a second
implementation).

## 1. TOF produces an off-delay at power-up although IN was never TRUE

Reported: https://github.com/ironplc/ironplc/issues/2545

- Reproducer: `conformance/timers/tof.st` / `.trace`, cycle 0.
- Expected (TOF timing diagram, ed.3 table 46): Q = FALSE until the first
  rising edge of IN; a falling edge needs a previous TRUE.
- IronPLC: cycle 0 with IN = FALSE gives `q=TRUE et=T#0ms`, then Q stays
  TRUE for PT (`notes/evidence/ironplc-run.txt`, `### conformance/timers/tof.st`).
- Cause (source): `vm/src/intrinsic.rs`, `tof`: the branch `else if !running`
  treats "IN FALSE and not running" as a falling edge. There is no previous-IN
  memory; the hidden `TIMER_RUNNING` flag starts at 0, so the first scan with
  IN = FALSE starts timing with Q = TRUE. matiec's `TOF` keeps `PREV_IN` and
  computes `Q := IN OR (STATE = 1)`.
- Consequence: any machine whose TOF input is FALSE at start sees its
  off-delayed output (a fan, a brake release, ...) energised for PT after
  power-up.

## 2. TP retriggers while IN stays TRUE (free-running oscillator)

Reported together with item 3: https://github.com/ironplc/ironplc/issues/2546

- Reproducer: `conformance/timers/tp.st` / `.trace`, cycles 9 to 11 and 16 to 17.
- Expected (TP timing diagram): after the pulse, Q stays FALSE until a new
  rising edge of IN; an IN held TRUE produces exactly one pulse.
- IronPLC: `9 => q=FALSE et=T#300ms`, `10 => q=TRUE et=T#0ms`,
  `11 => q=TRUE et=T#100ms`, ...: a new pulse starts on the scan after the
  pulse ends, for as long as IN is TRUE, i.e. Q oscillates with period PT +
  one cycle.
- Cause: `intrinsic.rs`, `tp`: `else if in_val` starts a pulse whenever
  `running` is 0 and IN is 1, with no rising-edge detection. matiec's TP has
  a third state (`STATE = 2`, "set") that is left only when IN is FALSE.

## 3. TP keeps ET = PT after the pulse when IN is already FALSE

- Reproducer: `conformance/timers/tp.st`, cycle 5 (`et` expected `T#0ms`,
  got `T#300ms`).
- Expected (diagram): ET returns to 0 once the pulse has ended and IN is
  FALSE.
- IronPLC: ET stays at PT until the next rising edge.
- Cause: same `tp` function, ET is only rewritten when a pulse is running or
  starts. Minor, but visible to a program that compares ET.

## 4. TON Q stays TRUE after PT is raised above the elapsed time

- Reproducer: `conformance/undefined/ton_pt_change.st`, cycles 5 to 9
  (`q=TRUE` with `et=T#400ms .. T#700ms` and PT = 800 ms).
- Status: not defined by the standard (PT is constant in the diagram), so
  recorded as implementation-defined, not a failure. matiec also keeps Q
  TRUE, but freezes ET at the old PT; IronPLC lets ET climb while Q is TRUE,
  so a program sees Q = TRUE together with ET < PT, a combination the
  diagram never shows.
- Cause: `ton` sets `TIMER_Q` to 1 when `et >= pt` and never clears it while
  IN stays TRUE.

## 5. INT addition wraps silently

- Reproducer: `conformance/undefined/int_overflow.st`.
- Status: permitted by the standard (ed.2 annex E lists range overflow as an
  implementer-specific error). matiec wraps too. Worth a line in IronPLC's
  documentation; a `--trap-on-overflow` compile option would make the
  behaviour explicit.

## 6. (Uncertainty, not an IronPLC defect) F_TRIG initial state

- Reproducer: `conformance/edge/f_trig.st`, cycle 0.
- IronPLC: `q=FALSE` on a first evaluation with CLK = FALSE (its hidden `M`
  starts at 0 and it computes `Q := NOT CLK AND M`, equivalent to the body
  with `M := TRUE`). matiec: `q=TRUE` (body from the 2001 FDIS with `M`
  default FALSE, `Q := NOT CLK AND NOT M`).
- The trace follows the ed.3 table 43 body as I recall it (`M : BOOL :=
  TRUE`). I do not have the standard text here, so this expectation is an
  assumption, flagged in the summary. If a reader with the text finds that
  ed.3 also leaves `M` at FALSE, the trace line for cycle 0 should become
  `q=?` and matiec's result is conformant.

## 7. CTU counts past PV (IronPLC) versus saturates at PV (matiec)

- Reproducer: `conformance/counters/ctu.st`, cycle 8; `undefined/ctu_pv_zero.st`.
- IronPLC: CV = 4 with PV = 3 (saturation only at the type maximum,
  `CounterValue::up` uses `saturating_add`). This matches the ed.3 body
  (`CV < PVmax`) as I recall it. matiec implements the 2001 FDIS body
  (`CV < PV`). Recorded as an IronPLC-conformant behaviour; the point is
  that the two open-source runtimes disagree, which is exactly what a
  conformance suite should pin down.

## 8. Division by zero is a VM trap that ends the scan

- Reproducer: `conformance/undefined/div_zero.st`, cycle 2: trap `divide by
  zero`, `--dump-vars` still available (`VmFaulted`).
- Status: a permitted reaction. Note that the whole program instance stops;
  there is no per-task error recovery, and `MOD` on the next line is never
  executed. Comparable to matiec, where the process gets SIGFPE.

## Not findings (checked and conformant)

- Operand evaluation order: left to right (both runtimes).
- FOR final value re-read each iteration (both runtimes); the program is
  non-conformant, not the runtime.
- Integer division truncates toward zero, `MOD` takes the sign of the
  dividend (`-7 / 2 = -3`, `-7 MOD 2 = -1`): conformant on both.
- `CASE` with lists and subranges, `IF/ELSIF/ELSE`, `FOR` with negative
  step and `EXIT`, `WHILE`, `REPEAT`, nested function calls, two FB
  instances with independent state, `R_TRIG`, `SR`, `RS`: conformant on
  both.

## Harness-level observations about IronPLC (not conformance issues)

- `ironplcvm run` cannot be used for conformance testing: no input
  injection and wall-clock time only (`notes/ironplcvm-io.md`).
- The MCP `run` tool's `stimuli` field is specified (REQ-TOL-mcp-042) but
  rejected at runtime ("not yet implemented"), so the MCP path cannot run
  this suite yet either.
- `EN` is reserved: an FB input named `en` is a syntax error (`P0002`). This
  is correct per the standard (EN/ENO are reserved), noted only because the
  first draft of `fb_two_instances.st` hit it.
