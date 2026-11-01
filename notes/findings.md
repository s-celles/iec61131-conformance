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

## 9. CTD and CTUD of INT wrap at the INT bounds instead of saturating

- Reproducer: `conformance/counters/ctd_bounds.st` (LD with PV = -32768,
  then a CD edge: CV = 32767) and `ctud_bounds.st` (LD with PV = 32767,
  then a CU edge: CV = -32768, then -32767).
- Expected: the ed.3 bodies count up only while `CV < PVmax` and down only
  while `CV > PVmin`; at the bound CV is unchanged. At PV = PVmax (or PVmin)
  the FDIS 2001 condition `CV < PV` (`CV > 0`) is false too, so both
  editions agree and matiec and RuSTy pass.
- This is ironplc#2332, closed on 2026-10-17 by the prefactoring PR #2346
  ("Fixes #2332" in the description of the planned follow-up); the 16-bit
  counting it describes is not in `5ea0610`, where `container/src/fb_type.rs`
  still says `CTU` and `CTU_INT` count with the 32-bit id.
  Reported there: https://github.com/ironplc/ironplc/issues/2332#issuecomment-6555649250

## 10. VAR_TEMP in a function block does not compile

- Reproducer: `conformance/pou/fb_var_temp.st`: `P9999 Capability is not
  implemented (yet!) / Starting value code generation does not support
  yet` on the `VAR_TEMP` declaration. The same semantics for a FUNCTION's
  VAR section (`pou/function_var_not_retained`) compile and pass.
- Known: ironplc#1969 (open).

## 11. MAX and MIN accept only two inputs

Reported: https://github.com/ironplc/ironplc/issues/2548
Fix proposed: https://github.com/ironplc/ironplc/pull/2551

- Reproducer: `conformance/ops/std_functions_ext.st`: `P4018 Function call
  has wrong number of arguments (function=MAX, expected=2, actual=3)`,
  likewise MIN. In the same program `ADD(a, b, c)` and `MUL(a, b, c)` are
  accepted, so this is the part of ed.3 6.6.1.7.3 (extensible functions,
  table 31 lists MAX and MIN as extensible) that ironplc#1618 (closed) did
  not cover.

## 12. (Not a defect) Timers with PT = 0 switch one cycle after the edge

- Reproducer: `conformance/undefined/timer_pt_zero.st`. Every timer makes
  its end-of-time test only on a cycle where it is already timing, so with
  PT = 0 TON's Q rises on the cycle after IN rises, TOF's Q falls on the
  cycle after IN falls, and TP gives a one-cycle pulse. Reading the
  diagrams at the limit PT = 0 would switch on the edge's own cycle, which
  is what matiec does (the only difference between the two, apart from
  item 1 at power-up). Recorded as implementation-defined.

## 13. Assigning a structure to a structure-typed field is not implemented

Reported: https://github.com/ironplc/ironplc/issues/2550

- Reproducer: `conformance/data/struct_internal.st` line 37, `r.tl := q;`
  with `r : RECT` whose field `tl : POINT`: `P9999 Statement code
  generation does not support yet`. The whole-variable copy `q := p;` on
  line 33 of the same program is accepted, so it is the nested target that
  is missing. Neighbouring open issues: ironplc#1471 (array-of-struct
  element), #2331 (structure output of an FB), #2523 (structure input
  field read).

## 14. `EN :=` in a function block invocation is a syntax error

Reported: https://github.com/ironplc/ironplc/issues/2549

- Reproducer: `conformance/pou/fb_en_eno.st` line 25, `c(EN := run_it,
  inc := inc);`: `P0002 Syntax error ... Found text 'EN' that matched
  token 'EN'`. The parser reserves `EN` (correct: an input named `en` is
  rejected too) but does not accept it as the implicit input of ed.3
  6.6.1.7 table 20; `c.ENO` is not reached. matiec executes the body only
  while EN is TRUE and reports ENO as the table says.

## 15. (Not a defect) Array index out of range is a trap

- Reproducer: `conformance/undefined/array_out_of_bounds.st`, cycle 2:
  trap `array index out of bounds: index 4 for array variable 3 with 4
  elements`, the scan stops. matiec performs no check and reads whatever
  follows the array (`v=4`). Both are permitted (annex E); recorded as
  implementation-defined with IronPLC's trap.

## 16. REAL_TO_INT and LREAL_TO_DINT truncate toward zero

- Reproducer: `conformance/ops/real_conversions.st`: 2.75 -> 2, -2.75 -> -2,
  -0.75 -> 0, 123456.75 -> 123456 (expected 3, -3, -1, 123457).
- Expected: ed.3 table 22 (ed.2 2.5.1.5.1): conversion from a real type to
  an integer type rounds to the nearest integer. matiec rounds (and, on
  ties, to the even integer, `__real_round` in `lib/C/iec_std_lib.h`).
- Known: ironplc#1813 (open). `undefined/real_to_int_ties` records the
  truncating behaviour on .5 values.

## 17. (Not a defect) REAL division by zero gives inf / -inf / NaN

- Reproducer: `conformance/undefined/real_div_zero.st`: 1.0/0.0 = inf,
  -1.0/0.0 = -inf, 0.0/0.0 = NaN, no trap, the scan continues (unlike the
  integer division trap of item 8). matiec does the same (IEC 60559
  through C). Recorded as implementation-defined.

## 18. (Limitation) One program instance, no SINGLE task

- Reproducers: every `conformance/config/` test but `globals_external`:
  `P9999 ... the compiler currently runs only one PROGRAM` (two program
  declarations or two instances of one program), tracked in ironplc#1613;
  `config/event_single.st`: `P4047 Task SINGLE parameter is not
  supported`.
- So the SPEC version 2 traces run on IronPLC only when the configuration
  has a single instance on a periodic task (`globals_external` passes:
  VAR_GLOBAL with an initial value, VAR_EXTERNAL reads and writes, task
  interval honoured by `run_round`). The VM itself schedules tasks in
  priority order (`vm.rs`, `run_round`), so #1613 is the only gap for
  `two_periods`, `priority_order` and `global_exchange`.

## 19. (Limitation) No API to write a STRING from outside the VM

- `VmRunning` offers `write_variable_raw` for scalar slots and a read-only
  `data_region()`; a string's content lives in the data region at the
  offset of the debug section's STRING layout entry, which the harness
  reads directly. Nothing writes it, so SPEC.md version 1 allows STRING
  outputs only and the `strings/` tests build their strings inside the
  program. The same limit would apply to `ironplcvm run --trace` and to
  MCP `stimuli` (ironplc#1163).
- Asked for on the proposal: https://github.com/ironplc/ironplc/issues/2547#issuecomment-6558044129

## 20. (Limitation) Edition 3 syntax: CONTINUE, METHOD

- Reproducers: `control-flow/continue.st` (`P0002` at `CONTINUE;`),
  `pou/fb_method.st` (`P0002` at `METHOD BUMP : INT`). Both are ed.3
  additions (7.3.3.4.2, 6.6.3.5); matiec, an ed.2 compiler, has CONTINUE
  but no METHOD; STruC++ has METHOD but no CONTINUE.

## 21. (Limitation) VAR_IN_OUT of a function block is not lowered

- Reproducer: `pou/fb_in_out.st`: `P9999 Capability is not implemented` at
  `acc := acc + inc;` inside the FB (`lowering/src/program.rs#L581`). The
  same `VAR_IN_OUT` on a FUNCTION (`SWAP`, and `TICK` in
  `undefined/short_circuit.st`) compiles and runs.

## 22. (Limitation) Array initialisers with structured elements

- Reproducers: `data/array_of_struct.st`, `[(x := 1, y := 10), ...]`, and
  `data/array_2d.st`, `[[10, 20, 30], [40, 50, 60]]` for an array of a named
  array type: both `P0002` at the first `(` or `[` of the initialiser (ed.3
  6.4.4.4.2, table 14). The flat initialiser of a two-dimensional array in
  the same test is accepted (the test fails only on the nested one).

## 23. (Defect) An input omitted from a formal function call is an error

- Reproducer: `pou/function_input_default.st`: `SCALE(x := x)` where `k` and
  `off` have initial values gives `P4018 Function call has wrong number of
  arguments (function=SCALE, expected=3, actual=1)`. Ed.3 6.6.1.7.1: in a
  formal call, the assignment of an input may be omitted and the input
  keeps its initial value; the same rule for function blocks
  (`pou/fb_input_defaults`) is honoured. matiec, its OpenPLC fork and
  STruC++ apply the default.

## 24. (Not a defect) Subrange and short-circuit corners

- `undefined/subrange_out_of_range`: a value outside `INT (5..10)` is
  stored unchecked (20, -3); the default initial value is the lower limit
  (5, `data/defaults` passes).
- `undefined/short_circuit`: `g AND f()` and `g OR f()` always call `f`
  (full evaluation), as do STruC++ and RuSTy; both matiecs short-circuit.
  Both are allowed by ed.3 7.3.2.
