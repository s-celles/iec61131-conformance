# Changelog

Notable changes are recorded here following Keep a Changelog.

## [Unreleased]

### Added

- Site: the state of every cited upstream issue and pull request (open, closed,
  merged, not planned), from the snapshot `notes/upstream-status.tsv` that
  `tools/site/upstream_status.py` refreshes. It is shown on the Upstream page, on
  each finding and among the recent reports on the home page. Also added: a
  Methodology page with the pipeline as a diagram, a Statuses page that defines
  every badge, a citation block from `CITATION.cff`, the data commit on every
  page with numbers, and chart tooltips that work with the keyboard, with a
  crosshair.
- Site: a History page, with the suite's size, each runtime's share of
  conformant tests passed (small multiples on one scale) and the upstream
  issues cited, over time. It is read from the git history of
  `notes/comparison.md` at build time, so the Site workflow checks out the
  full history. Each point has a tooltip, and a filterable table holds every
  value.
- `harness/trust`: the suite runs against truST
  (johannesPettersson80/trust-platform), which compiles Structured Text to
  native code. `run.py` feeds the records, one per line, to truST's
  `conformance_driver` and compares its output with the shared `tracefmt`
  rules; the CI job `trust` builds the driver and truST's native toolchain at
  `TRUST_SHA` and diffs against `notes/evidence/trust-run.txt`.
- `tools/monitor`: rules read off the text of ed.2 for R_TRIG, F_TRIG, SR, RS,
  CTU, CTD, CTUD (block bodies) and TON, TOF, TP (timing diagrams), checked
  cycle by cycle on the expected traces and on every runtime's recorded
  output, as an oracle independent of the AI-written traces. CI fails if an
  expected trace violates a rule; each block test's page on the site shows
  the result per runtime.
- `notes/trace-audit-2026-11-18.md`: the edition 2 citations of the traces and
  the five conformant traces most runtimes fail, checked against the text of
  IEC 61131-3:2003. `edge/f_trig`, `ops/limit_inverted`, `data/defaults` and
  `config/priority_order` are confirmed. `pou/fb_en_eno` treats EN/ENO on a
  function block as implicit, where ed.2 makes it optional: it stays
  conformant with a note (a compile rejection is a missing optional feature),
  and ironplc#2549 and PLC-lang/rusty#2036 were corrected in a comment.
- Fuzz exclusion `bit_not_compare`: no bit-string NOT inside an operand of `=`
  or `<>` (matiec item 19, beremiz/matiec#54). Programs generated without it
  are unchanged.
- Site: a findings registry, one page per finding of the notes (runtime,
  status, upstream issues, tests) in a filterable, sortable table (as in
  julia-findings), also used for the results table; test pages list the
  findings that cite them. The home page shows the banner.
- Project site on GitHub Pages (https://s-celles.github.io/iec61131-conformance/):
  results, a page per test with its program, trace and recorded outputs, the
  runtimes' deviations, the cited upstream issues and the documents, plus
  `llms.txt` and `llms-full.txt`. `tools/site/sitegen.py` generates the pages
  at build time, outside the repository, and `.github/workflows/site.yml`
  builds them with Hugo and Hextra and deploys them.
- Conformance test `ops/not_compare`: NOT on a BYTE or WORD compared
  directly, from the fourth fuzz round of 2026-11-16 (matiec item 19).
- Three conformance tests from the third fuzz round of 2026-11-16: a MUX
  whose selector is a MUX call (`ops/mux_nested_selector`), duration
  literals with milliseconds (`ops/time_literal_ms`), and `=` / `<>`
  between a STRING and its prefix (`strings/compare_prefix`), with the
  evidence of all seven runtimes.
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
- Fuzz exclusions `call_in_args` (an F_TICK / F_DM call inside another
  call's argument, matiec item 17) and `call_divisor` (such a call as a
  `MOD` divisor, matiec item 16). Programs generated without them are
  unchanged.
- Fuzz exclusion `mux_selector_call`: no MUX call inside a MUX selector
  (RuSTy item 10). Programs generated without it are unchanged.
- `shell.nix` with CI's toolchains (gcc 13, Node 22, rustup) for building the
  runtimes on NixOS.

### Changed

- README, guide, site and `CITATION.cff` say who wrote the expected values:
  an AI assistant, from its knowledge of IEC 61131-3, without the standard's
  text, so derivations and clause numbers are not checked against it. They
  no longer say the traces were derived by hand or checked by the author. A
  disclaimer (individual, non-commercial, not endorsed by any standards or
  accredited body) is on the README and on every page of the site.
- The README is a short overview; the method, layout, CI and per-runtime
  instructions moved to `docs/guide.md`, which the site renders as its Guide.
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

- Site: a link anchor such as `notes/findings.md#28` was counted as an upstream
  issue.
- `pou/fb_method` declares its methods PUBLIC: without an access specifier a
  method is PROTECTED in ed.3 and may not be called from `main` (issue #15).
  The ed.3 citations are corrected to 6.6.7.2 and table 53. No expected value
  changed.
- CI's `trust` job builds without truST's `sccache` rustc wrapper, which the
  runner lacks (`RUSTC_WRAPPER` set empty).
- The OpenPLC fork's evidence for `ops/time_literal_ms` cited trace lines
  shifted by a comment edit; `harness/check_trace_lines.py`, now in CI's
  `formal` job, checks every such reference without running a runtime.
- Ed.2 clause and table numbers in the comments of 22 traces (control-flow
  clauses cited from SFC, initialisation from declaration, operator tables off
  by one, TIME * ANY_NUM from table 24 instead of 30, among others). No
  expected value changed.
- The fuzz generator no longer writes a constant subexpression whose value
  leaves its type's range (`UINT#6 - UINT#8`, `DINT_TO_UINT(-17)`, a negative
  TIME difference) in a branch that never runs: IronPLC and matiec reject it at
  compile time. Programs of the `wide` and `time` profiles change for the
  seeds that had one; the other profiles are unchanged.
- C/C++ build-error excerpts mask library paths before truncation, so
  checkout path length cannot change the recorded cut-off point.
- README totals distinguish the 83 conformant and 18 implementation-defined
  cases in the resulting 101-test suite.
