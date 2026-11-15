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
- String oracle and build-diagnostic regression checks, also run in CI.

### Changed

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
