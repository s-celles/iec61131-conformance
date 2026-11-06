# Findings: IronPLC behaviours that differ from the standard or from matiec

IronPLC commit `6e40df2` (0.252.0; until 2026-11-06 `5ea0610`, 0.251.0). Every item has a reproducer in
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

## 6. (Resolved 2026-11-02) F_TRIG initial state

- Reproducer: `conformance/edge/f_trig.st`, cycle 0 (CLK = FALSE on the
  first evaluation).
- The text settles it. IEC 61131-3 ed.3 6.6.3.5.3, table 45 declares
  `F_TRIG` with `VAR M : BOOL; END_VAR` (no initial value, so FALSE) and the
  body `Q := NOT CLK AND NOT M; M := NOT CLK;`, and the NOTE under the table
  says that an `F_TRIG` "whose CLK input is disconnected or is connected to
  a value of FALSE" has Q at BOOL#1 after its first execution following a
  cold restart, BOOL#0 after that. So `q=TRUE` at cycle 0.
- Until 2026-11-02 the trace assumed `M : BOOL := TRUE` ("as I recall it",
  flagged here as the suite's main uncertainty) and expected `q=FALSE`;
  adclz pointed at table 45 on adclz/rk#117, and the trace, its derivation
  and the Lean model (`F_TRIG false`) were corrected from the table's text.
- IronPLC computes `Q := NOT CLK AND M` with its hidden `M` at 0, which is
  the `M := TRUE` reading: `q=FALSE` at cycle 0, a deviation from table 45.
  matiec's FDIS-2001 body is the standard's.
- The suite also cited the wrong tables for the standard function blocks:
  table 43 of ed.3 is "Function block call"; the edge detectors are table
  45 (6.6.3.5.3) and the counters table 46 (6.6.3.5.4).

## 7. (Not a defect) CTU counts past PV (IronPLC) or stops at PV (matiec)

- Reproducer: `conformance/counters/ctu.st`, cycle 8; `undefined/ctu_pv_zero.st`.
- IronPLC: CV = 4 with PV = 3 (saturation only at the type maximum).
  matiec, its OpenPLC fork, STruC++ and rk stop at PV (`CV < PV`, the 2001
  FDIS body), and at 0 counting down.
- Both are permitted. The ed.3 bodies (6.6.3.5.4, table 46) count while
  `CV < PVmax` and `CV > PVmin`, and the NOTE under the table says "The
  numerical values of the limit variables PVmin and PVmax are implementer
  specific." Until 2026-11-02 the counter traces assumed the INT range and
  reported the runtimes that stop at PV or 0 as failing; they now leave CV
  unchecked on the cycles where the limits decide (Q, QU, QD still checked).

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
- Expected: the ed.3 bodies (table 46) count up only while `CV < PVmax` and
  down only while `CV > PVmin`. The limits are implementer specific but are
  values of CV's type, so at CV = 32767 (-32768) no choice allows a count:
  CV is unchanged. A wrap is a defect whatever the limits.
- This is ironplc#2332, closed on 2026-10-17 by the prefactoring PR #2346
  ("Fixes #2332" in the description of the planned follow-up); the 16-bit
  counting it describes is not in `5ea0610` nor in `6e40df2` (0.252.0), where `container/src/fb_type.rs`
  still says `CTU` and `CTU_INT` count with the 32-bit id.
  Reported there: https://github.com/ironplc/ironplc/issues/2332#issuecomment-6555649250

## 10. VAR_TEMP in a function block does not compile

- Reproducer: `conformance/pou/fb_var_temp.st`: `P9999 Capability is not
  implemented (yet!) / Starting value code generation does not support
  yet` on the `VAR_TEMP` declaration. The same semantics for a FUNCTION's
  VAR section (`pou/function_var_not_retained`) compile and pass.
- Known: ironplc#1969 (open).

## 11. (Resolved in 0.252.0) MAX and MIN accept only two inputs

Reported: https://github.com/ironplc/ironplc/issues/2548
Fixed by https://github.com/ironplc/ironplc/pull/2551 (merged; in 0.252.0,
`6e40df2`): `ops/std_functions_ext` passes.

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

- Reported: https://github.com/ironplc/ironplc/issues/2552

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

## 25. (Defect) SHL keeps the bits shifted beyond the width of its input

- Reported: https://github.com/ironplc/ironplc/issues/2553
- Reproducer: `ops/shl_width.st`: `SHR(SHL(b, 7), 4)` with `b : BYTE :=
  16#44` gives 16#20 (so `SHL(16#44, 7)` was 16#2200, not 16#00) and
  `SHR(SHL(w, 12), 8)` with `w : WORD := 16#67CB` gives 16#7CB0; the
  value is only masked when it finally reaches the BYTE/WORD variable.
  `ROL` and `ROR` do work within the width (`b_rol`, `w_ror` pass), as
  does `SHL` alone (`ops/bit_ops`). Ed.3 table 30 / ed.2 table 25: the
  result of `SHL(IN, N)` has the type of `IN`. Found by `tools/fuzz`.

## 26. (Defect) An untyped based literal is ANY_INT, not usable as a bit string

- Reported: https://github.com/ironplc/ironplc/issues/2554
- Reproducer: `ops/bit_literals.st`: `ob := 16#A5` with `ob : BYTE` is
  `P4035 Assignment value type does not match (value_type=ANY_INT)`,
  `b AND 16#0F` is `P4049 Operator is not defined for the operand types
  (expected=ANY_BIT, actual=ANY_INT)`, `SHL(16#0001, n)` is `P4026`, and
  `(w AND 16#00FF) = 16#0055` is `P4049`. Ed.3 6.3.2 table 5 (ed.2 2.2.1
  table 2): a based literal takes its type from the context, bit-string
  types included; the typed forms `BYTE#16#FF`, `WORD#16#1234` are
  accepted. matiec, its fork and STruC++ accept the untyped form. Found
  by `tools/fuzz`.

## 27. (Defect) MIN, MAX and LIMIT do not accept TIME

- Reported: https://github.com/ironplc/ironplc/issues/2555
- Reproducer: `ops/time_functions.st`: `MIN(a, b)` with `a, b : TIME` is
  `P4026 Function call argument type does not match parameter type
  (function=MIN, parameter=IN1, expected=ANY_NUM, actual=time)`, likewise
  `MAX` and `LIMIT`. Ed.3 table 32 (ed.2 table 27) declares the three on
  `ANY_ELEMENTARY`, which includes TIME (durations are ordered, table 33
  / ed.2 table 28; `LT(a, b)` and `a < b` on TIME are accepted). `SEL` and
  `MUX` on TIME are accepted. matiec's OpenPLC fork and STruC++ compute
  the test. Found by `tools/fuzz` (profile `time`).
