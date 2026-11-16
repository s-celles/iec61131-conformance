# Changelog

Notable changes are recorded here following Keep a Changelog.

## [Unreleased]

### Added

- Five conformance tests for INSERT positions, signed FIND results,
  extensible CONCAT, STRING MIN/MAX/LIMIT, and extensible MIN/MAX with
  arithmetic inputs in different positions.
- Two conformance tests for an array element as a function's VAR_IN_OUT
  and as the target of its VAR_OUTPUT (`pou/inout_array_element`,
  `pou/output_array_element`).
- Local upstream report drafts and a reproducible fuzz campaign report.
- Fuzz profile `arrays`: INT arrays `ARRAY[-2..2]` (with an initialiser),
  `ARRAY[1..4]` and `ARRAY[0..1, 1..3]` read and written with computed
  subscripts, also from FOR loops; `--exclude array_index_expr` keeps the
  subscripts to literals and variables.
- Fuzz profile `array_calls`: the arrays with the user POUs of `calls`,
  array elements also as VAR_IN_OUT and VAR_OUTPUT arguments
  (`--exclude array_elem_args` leaves those out).
- Four conformance tests for structures: member initial values and a partial
  initialiser with a BOOL member (`data/struct_init`), copies to and from an
  array element (`data/struct_element_copy`), a structure member as a
  function's VAR_IN_OUT and as the target of its VAR_OUTPUT
  (`pou/inout_struct_field`, `pou/output_struct_field`), with evidence for
  IronPLC, matiec, the OpenPLC fork, STruC++, rk and 4diac.
- Fuzz exclusions `struct_elem_copy` and `struct_field_inout`; with
  `array_elem_args`, no member of an array element is passed as an argument.
- Fuzz profiles `structs` and `struct_calls`: a structured type with a field
  initial value, variables with and without an initialiser and an array of
  structures, fields read and written, whole structures copied, and (with the
  user POUs) INT fields as VAR_IN_OUT and VAR_OUTPUT arguments
  (`--exclude struct_copy,struct_init,struct_field_args`).
- String oracle and build-diagnostic regression checks, also run in CI.
- `shell.nix` with CI's toolchains (gcc 13, Node 22, rustup) for building the
  runtimes on NixOS.

### Changed

- matiec pinned at upstream c316fe5 (was 3a41303): `config/priority_order`,
  `strings/functions`, `ops/date_time`, `ops/time_arith` and
  `ops/time_functions` now pass (upstream fixes of beremiz/matiec#43, #41
  and #40), and `ops/time_mul` builds and fails on the `__time_mul`
  overflow (beremiz/matiec#51); matiec passes 77 of the 87 conformant tests.
- RuSTy evidence rerun at the pinned e911ee5 over all 105 tests (it covered
  89): 70 of the 87 conformant tests pass; the one new deviation is MIN, MAX
  and LIMIT on STRING, which compile but do not link (RuSTy item 9).
- The in-progress STRING fuzz profile now generates CONCAT with two to
  four inputs and can exclude INSERT, REPLACE, signed LEN/FIND expressions
  and extensible CONCAT when searching beyond known defects.
- Runtime evidence and comparison totals include all 101 conformance cases,
  with build diagnostics recorded after path masking; pinned runtime
  revisions are unchanged.

### Fixed

- C/C++ build-error excerpts mask library paths before truncation, so
  checkout path length cannot change the recorded cut-off point.
- README totals distinguish the 83 conformant and 18 implementation-defined
  cases in the resulting 101-test suite.
