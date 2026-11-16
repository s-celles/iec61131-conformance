# Local upstream findings, 2026-11-07

These entries are local report drafts, not published issues. Results refer
to the commits pinned in `.github/workflows/ci.yml`; they do not assert
that the latest upstream revision is affected. Full programs, hand-derived
traces and observed results are in the linked files. Earlier reported
findings remain in [notes/findings.md](notes/findings.md) and
[notes/comparison.md](notes/comparison.md).

## STruC++ `72dfcb8`: INSERT is one character early

- Reproducer: [insert_positions.st](conformance/strings/insert_positions.st),
  [trace](conformance/strings/insert_positions.trace).
- `src='abcde'`, `part='XY'`, `INSERT(src,part,2)`:
  expected `'abXYcde'`, observed `'aXYbcde'`. P=1 inserts at the beginning;
  P=5 inserts before the final character instead of appending.
- IEC 61131-3 ed.3 table 34 defines INSERT after character P. The existing
  general string test uses literals and fails to build before it can
  observe this independent defect. IronPLC, both matiecs and 4diac agree
  with the reduced trace.
- Cause: [iec_string.hpp](https://github.com/Autonomy-Logic/STruCpp/blob/72dfcb8b1c5a41a68bfbf4b133169189c58f04b3/src/runtime/include/iec_string.hpp)
  passes `pos - 1` to the zero-based `insert`; DELETE/REPLACE start at P,
  but INSERT starts after P.

## STruC++ `72dfcb8`: extensible MIN/MAX reject expression inputs

- Reproducer: [minmax_ext_expr.st](conformance/ops/minmax_ext_expr.st),
  [trace](conformance/ops/minmax_ext_expr.trace); reduced from `calls` seed 166.
- With INT variables a=3, b=7, c=2, `MAX(a*2,b,c)` should return 7.
  The ST is accepted, but g++ reports no matching MAX overload. Moving
  the expression to the last position, `MAX(b,c,a*2)`, builds and gives 7.
  MIN has the same defect. No literal arguments, overflow or side effects.
- Cause: [iec_std_lib.hpp](https://github.com/Autonomy-Logic/STruCpp/blob/72dfcb8b1c5a41a68bfbf4b133169189c58f04b3/src/runtime/include/iec_std_lib.hpp)
  uses `MAX(T first, T second, U third, ...)` and likewise MIN. The first
  two C++ types must be identical, but arithmetic with a constant promotes INT to C++ int
  while variables remain `IECVar<short>`. The mixed-type two-input overload
  does not rescue deduction for a three-input call. Table 32 makes MIN/MAX
  extensible; IronPLC and both matiecs pass.

## STruC++ `72dfcb8`: extensible CONCAT lacks variable overloads

- Reproducer: [concat_ext.st](conformance/strings/concat_ext.st),
  [trace](conformance/strings/concat_ext.trace).
- `CONCAT(a,b,c)` with STRING variables `'ab'`, `'CD'`, `'ef'` should yield
  `'abCDef'` (ed.3 table 34, extensible calls 6.6.1.7.3). ST compiles to
  C++, but g++ finds no matching CONCAT overload. Four inputs also fail;
  the nested two-input form works. Both matiecs pass the extensible call.
- The variadic overload in `iec_string.hpp` accepts `IECString`, while
  only two-input overloads accept the generated `IECStringVar` wrappers.
  This does not require string literals or `STRING[n]` syntax.

## STruC++ `72dfcb8`: MIN/MAX/LIMIT omit STRING

- Reproducer: [min_max_limit.st](conformance/strings/min_max_limit.st),
  [trace](conformance/strings/min_max_limit.trace).
- STRING variables `'abc' < 'abd' < 'abe'` are valid ANY_ELEMENTARY inputs
  (ed.3 table 32). `MIN(a,b)`, `MAX(a,b)` and `LIMIT(a,c,b)` are accepted
  as ST but rejected by g++'s overload deduction.
- `iec_traits.hpp` does not give either string class the ANY_ELEMENTARY
  trait required by the function templates. Both matiecs and 4diac pass.
  Equal lengths and ordered LIMIT bounds avoid the known prefix comparison
  and inverted-bounds issues.

## IronPLC `6e40df2` (0.252.0): CONCAT still requires two inputs

- Reproducer: [concat_ext.st](conformance/strings/concat_ext.st).
- P4018: `function=CONCAT, expected=2, actual=3` (also actual=4).
- CONCAT is extensible (ed.3 table 34). The same test passes both matiecs;
  the nested two-input form works on IronPLC. MIN/MAX extensibility was
  fixed in ironplc#2551, but that fix does not cover CONCAT.
- `analyzer/src/intermediates/stdlib_function.rs` registers CONCAT using
  `FunctionSignature::stdlib` with exactly IN1 and IN2; it is not marked
  extensible, so the rejection precedes code generation.
- See [finding 28](notes/findings.md#28-defect-concat-accepts-only-two-inputs).

## rk `20761dd`: CONCAT and ordered string selection are missing overloads

- `strings/concat_ext` refuses three/four CONCAT inputs; `stdlib/Strings.st`
  declares only two inputs. `strings/min_max_limit` refuses STRING inputs;
  `stdlib/Selection.st` omits STRING for MIN/MAX/LIMIT. These constructs are
  in ed.3 tables 34 and 32 respectively.
- Record these as missing standard functionality; no claim about their
  priority in rk's documented scope. Both matiecs execute both tests;
  4diac executes the string selection test.

## matiec `3a41303` (and OpenPLC `b5d4135`): an array element as a function's VAR_IN_OUT or VAR_OUTPUT does not build

Added 2026-11-15. Reported: https://github.com/beremiz/matiec/issues/53
Still present at matiec `c316fe5` (2026-11-16, issue open).

- Reproducers: [inout_array_element.st](conformance/pou/inout_array_element.st),
  [output_array_element.st](conformance/pou/output_array_element.st), and their traces.
- `r := BUMP(arr[i], 5)` (n is BUMP's VAR_IN_OUT) and
  `q := DIVMOD(a := x, b := 4, m => arr[i])` with `arr : ARRAY[1..3] OF INT`:
  iec2c accepts the ST, gcc rejects the generated C with
  "`__ARRAY_OF_INT_3` has no member named `tabledata__`". The wrapper prints
  `data__->ARR.value.tabledata__->I` instead of
  `data__->ARR.value.table[(data__->I) - (1)]`. A literal subscript gives
  `table__ULINT_LITERAL(0)` (fuzz seed 13, `a0[0]`). The OpenPLC fork fails on the same line ("assignment
  to expression with array type"). A function block's output to an element
  (`d(x := 3, y => arr[i])`) builds and runs.
- Expected: VAR_IN_OUT refers to the caller's variable and `=>` assigns the
  output to a variable (ed.3 6.6.2.3, 6.6.1.7.1 table 20); an array element
  is a variable (ed.3 6.4.4.3, 7.3.1; ed.2 2.4.1.2). STruC++ and rk compute
  both traces, and IronPLC computes the VAR_OUTPUT one.
- Cause: `stage4/generate_c/generate_c_inlinefcall.cc`,
  `visit(array_variable_c)`, prints `.table` and then visits
  `subscript_list`, but `generate_c_inlinefcall_c` has no
  `visit(subscript_list_c)`; `generate_c_st.cc` has one, which prints
  `[(sub) - (lower bound)]` per dimension. Still so on matiec `master`
  (2026-11-15). Found by `tools/fuzz` (profile `array_calls`): 19 of 120
  seeds.

## IronPLC `6e40df2` (0.252.0): an array element cannot be a VAR_IN_OUT argument

Added 2026-11-15. Reported: https://github.com/ironplc/ironplc/issues/2615

- Reproducer: [inout_array_element.st](conformance/pou/inout_array_element.st).
- `BUMP(arr[i], 5)` and `BUMP(n := arr[3], d := 1)` are P9999 "Statement code
  generation does not support yet". The VAR_OUTPUT form
  (`m => arr[i]`, `pou/output_array_element`) passes.
- `codegen/src/body/mod.rs` `args_can_emit`: `Arg::Ref(place)` must resolve
  through `place::variable_name` to a named variable; an indexed place does
  not. Still so on `main` (2026-11-15). 13 of 120 `array_calls` seeds.
- See [finding 29](notes/findings.md#29-defect-an-array-element-cannot-be-passed-to-a-functions-var_in_out).

## Extensions of existing findings

- STruC++'s unsigned LEN result also affects FIND: `FIND('abc','bc')=2`,
  but `MAX(FIND(src,part), i0)` with i0=-11 returns -11, MIN returns 2 and
  `FIND(src,part)>i0` is FALSE. [find_int.st](conformance/strings/find_int.st)
  isolates the same `size_t` cause. IronPLC, matiec and 4diac pass.
- IronPLC's ANY_NUM restriction on MIN/MAX/LIMIT (ironplc#2555 for TIME)
  also excludes STRING. `strings/min_max_limit` extends finding 27.
- OpenPLC's FIND-not-found result and rk's UDINT string indices appear in
  the new tests too; both were already documented. No new bug count is
  assigned to those results.

Assisted-by: AI

## OpenPLC `b5d4135` (matiec fork): a structure initialiser rejects non-integer literals

Added 2026-11-16. Not reported upstream.

- Reproducer: [struct_init.st](conformance/data/struct_init.st) and its trace.
- `c : CFG := (k := 3, flag := TRUE);` with `flag : BOOL` gives "Initialization
  element identifier (flag) is not declared in referenced structure/FB scope, or
  is set to value of incompatible datatype". In reductions, a TIME member
  (`T#1s`), a REAL member (`1.5`) and `BOOL#TRUE` give the same error. Integer
  literals pass, also into a BOOL member (`flag := 1`) and into a WORD member
  (`16#00FF`), in any member order. Upstream matiec `3a41303` and `c316fe5` accept every case.
  This is the same message as fork item 7 (structure initialisers inside an
  array initialiser), so the two may share a cause.
- Expected: a structure initialiser assigns a constant of each named member's
  type, and leaves the other members at the type's initial values (ed.3
  6.4.4.4.2, table 10; ed.2 2.3.3.1, 2.4.2). The other six runtimes compute the
  trace.
- Found by `tools/fuzz` (profile `structs`): the fork rejected every one of
  the 999 defined programs, all on `p1 : PT := (x := 2, ok := TRUE)`.

## Extensions of existing findings, 2026-11-16 (structures)

- IronPLC's VAR_IN_OUT restriction (ironplc#2615, finding 29) also covers a
  structure member: `BUMP(p.x, 5)` and `BUMP(pa[i].x, 1)` are P9999
  (`pou/inout_struct_field`). Same cause: `place::variable_name` returns only
  `Access::Named`, and a member access is not one. The VAR_OUTPUT forms
  (`m => p.y`, `m => pa[i].y`, `pou/output_struct_field`) pass. This could be
  added as a comment on #2615, which has not been done.
- IronPLC's whole-element assignment of an array of structures (open upstream
  issue ironplc#1471) shows in both directions, `pts[i] := p` and
  `c := pts[i]` (`data/struct_element_copy`). `data/array_of_struct`, which
  has `c := pts[3]`, stops earlier on its array initialiser (finding 22).
  This was 650 of the 665 IronPLC failures in the structure campaigns. The
  other 15 are a member passed to F_TICK's VAR_IN_OUT (first item).
- matiec item 18 (beremiz/matiec#53) also covers a member of an array
  element: `BUMP(pa[i].x, 1)` and `m => pa[i].y` give "`__ARRAY_OF_PT_3` has
  no member named `table__ULINT_LITERAL`" (`tabledata__` with a variable
  subscript; `pou/inout_struct_field`, `pou/output_struct_field`). A member of a plain structured variable
  (`p.x`) builds and runs. The OpenPLC fork gives "has no member named
  `table2`" (fork item 13). This was 23 of the 40 matiec failures in
  `struct_calls`. The other 17 are item 17, a VAR_IN_OUT call inside another
  call's argument.

## RuSTy `e911ee5`: a MUX whose selector is a MUX call crashes `plc`

Added 2026-11-16. Not reported.

- Reproducer: [mux_nested_selector.st](conformance/ops/mux_nested_selector.st),
  [trace](conformance/ops/mux_nested_selector.trace). Minimal program:

  ```
  PROGRAM main
    VAR k : INT; a : INT; b : INT; r : INT; END_VAR
    r := MUX(MUX(k, a, b), a, b);
  END_PROGRAM
  ```

- `plc -c` exits on SIGSEGV (rc 139) in LLVM's
  `LowerExpectIntrinsicPass::run`, reached from
  `GeneratedModule::persist_to_obj` -> `Module::run_passes`. `plc --ir`
  stops with "Builder error: ... error: label expected to be numbered '5'
  or greater", so the IR generated for the inner MUX is already invalid
  before any pass runs.
- `MUX(ABS(MUX(k, a, b)) MOD 4, ..)` and `MUX(k + MUX(k, a, b), a, b)` crash
  too. A SEL, MAX or ABS as selector, a MUX as an input (`MUX(k, MUX(..),
  b)`), `ABS(MUX(..))` and `MUX(..) + MUX(..)` compile.
- Ed.3 table 32 declares K as ANY_INT, and 7.3.2 allows any expression of
  that type as a function input. IronPLC, both matiecs, STruC++ and rk
  give the derived trace. 4diac lacks `func_MUX.h` (an existing finding).
- In the third fuzz round of 2026-11-16 this was every RuSTy divergence:
  34 programs in `calls`, `time` and `strings`.

## Extensions of existing findings, 2026-11-16 (third fuzz round)

- OpenPLC fork item 4 (TIME literal truncation, beremiz/matiec#44) is not
  AArch64-only. On x86-64, 80-bit `long double` still truncates
  `T#4748ms` to 4747999999 ns, `T#3496ms` to 3495999999 ns and `T#4ms` to
  3999999 ns, about half of the millisecond literals below 100 s
  (`ops/time_literal_ms`; `T#4s219ms` and `T#1263ms` are exact). Upstream
  matiec `c316fe5` rounds to the nearest (7a86468) and passes. Upstream
  `3a41303` had the same macro as the fork.
- OpenPLC fork item 1 (`__STR_CMP` stops at the shorter length) also makes
  `'ab' = 'abc'` and `'' = 'abc'` TRUE, and `<>` FALSE
  (`strings/compare_prefix`). All 13 fork divergences of the `strings`
  campaign pass with upstream's `__str_cmp` in a patched copy of the
  fork's `lib`.

## matiec `c316fe5` (and OpenPLC `b5d4135`): NOT on a BYTE or WORD compared directly

Added 2026-11-16. Not reported.

- Reproducer: [not_compare.st](conformance/ops/not_compare.st),
  [trace](conformance/ops/not_compare.trace). With `b : BYTE := 16#00` and
  `c : BYTE := 16#FF`, `(NOT b) = c` is FALSE and `(NOT b) <> c` TRUE; the
  same with WORD (`NOT 16#0F0F` against `16#F0F0`).
- Generated C: `__SET_VAR(data__->,Q1,,(~(__GET_VAR(data__->B,)) ==
  __GET_VAR(data__->C,)));`. C's integer promotion widens the `BYTE`
  (`uint8_t`) to `int` before `~`, so `~0x00` is -1 and differs from 255.
  Ed.3 table 33 gives NOT the operand's bit-string type, so `NOT 16#00` is
  the BYTE `16#FF`.
- A cast back to the operand's type around `~` in stage 4 would fix it.
  When the result is stored first (`x := NOT b`) it is truncated, which is
  why the existing bit tests pass. IronPLC, STruC++, RuSTy, rk and 4diac
  give the derived trace.
- Found by `tools/fuzz` (profile `wide`, seeds 6091 and 6148 of the fourth
  round).
