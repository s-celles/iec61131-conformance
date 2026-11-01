# Proposal to IronPLC: an open, runtime-agnostic IEC 61131-3 conformance trace suite

Draft of the issue to open on ironplc/ironplc once #2545 and #2546 have
been looked at. Supersedes the earlier `ISSUE_FINAL.md`.

**Title:** Proposal: an open, runtime-agnostic IEC 61131-3 conformance trace suite (18 tests, CC0)

---

## What

https://github.com/s-celles/iec61131-conformance — plain `.st` programs
paired with plain-text expected I/O traces, one record per scan cycle
(inputs applied at cycle start, outputs sampled at cycle end, simulated time
`t = cycle * period`). No dependency on IronPLC: the same files run against
matiec and RuSTy.

- 12 `status: conformant` tests: TON, TOF, TP, R_TRIG, F_TRIG, SR/RS, CTU,
  IF/CASE, FOR+EXIT, WHILE/REPEAT, function calls, a function block with
  two instances. Scope BOOL/INT/DINT/UINT/TIME, one program, one cyclic
  task. Expected values derived by hand from the standard's bodies and
  timing diagrams, with the derivation as a comment in each `.trace`.
- 6 `status: implementation-defined` tests recording what IronPLC does on
  corners the standard leaves open (INT overflow, division by zero, operand
  evaluation order, TON with a changing PT, FOR bound modified in the loop,
  CTU with PV = 0), with what the standard says next to it.
- A Lean 4 model of the function blocks; `lake build` proves each
  conformant trace of those blocks is the model's output.
- CI runs the suite against pinned commits of the three runtimes and diffs
  against recorded results, so any drift in a runtime or a trace is visible.

## Why IronPLC might want it

Running it on `5ea0610` found #2545 (TOF off-delay at power-up) and #2546
(TP retrigger with IN held, ET not cleared). Both were locked in by existing
tests, which is the kind of thing an independent oracle catches. The other
ten conformant tests pass. With #2288 (ADR-0060, standard blocks generated
by lowering) ahead, a runtime-independent regression set for exactly those
blocks seems timely.

Differential results (`notes/comparison.md`): IronPLC 10/12, matiec 10/12,
RuSTy 8/12; the three disagree on timer edges, `F_TRIG` start-up, `SR`/`RS`
input names and `CTU` above `PV`.

## How the suite drives IronPLC today

`ironplcvm run` has no input path and runs on the wall clock, `ironplcvmd`
refuses `setVariable`, and the MCP `run` tool's `stimuli` is specified
(REQ-TOL-mcp-042) but still rejected (#1163). The suite therefore links the
`ironplc_vm` crate directly (`harness/ironplc`, ~300 lines):
`write_variable_raw` per input, `run_round(cycle * period)`,
`read_variable_raw` per output, names resolved through
`DebugSection::program_variable`. The 18 tests run in well under a second.

## Questions

1. Would you host the suite (`tests/conformance/`?), or prefer it to stay
   external and be referenced from a `specs/design/` document with `REQ-`
   ids like the other requirement-tagged tests? #1373 (test compatibility
   libraries with ST programs executed by the VM) seems to be the same
   need from the other side.
2. Which public surface would you want a CI run to use:
   (a) a `--trace FILE` option on `ironplcvm run` (reads the trace header,
   replaces the clock by `cycle * period`, writes inputs before each
   `run_round`, renders outputs with `VariableRenderer`; ~150 lines in
   `vm-cli`, no VM change) — I would be glad to contribute it;
   (b) finishing `stimuli` (#1163) and running through MCP; or
   (c) a harness crate in `compiler/` next to the
   `codegen/tests/it/end_to_end_*.rs` step scripts, whose
   `write`/`run`/`expect` form the trace format mirrors line for line.
3. For the implementation-defined corners, would you rather IronPLC's
   choices be documented (wrap on INT overflow, trap on division by zero,
   left-to-right evaluation, FOR bound re-read every iteration) or made
   explicit by compiler options?

Assisted by AI.
