# ISSUE_FINAL.md

`ISSUE_DRAFT.md` was not available in this working session (the prompt
referred to it "next to this prompt" but only the prompt was attached), so
this file contains the two pieces the brief asked to change, ready to be
merged into the draft, followed by a complete issue body to use if the draft
is not at hand. Nothing has been posted anywhere.

---

## Replacement for question 2 (how ironplcvm can be driven)

> **2. Driving the VM from a test.** I looked at how a program's inputs can
> be set and outputs read from outside the VM on commit `5ea0610`:
>
> - `ironplcvm run` has no input path at all (`vm-cli/src/cli.rs`, `run`):
>   it loops `run_round(start.elapsed(), ..)` on the wall clock and can only
>   dump the final image with `--dump-vars`. So the CLI cannot run a
>   per-cycle trace, and timer tests through it are not reproducible.
> - `ironplcvmd` (DAP) refuses `setVariable`/`evaluate`.
> - The MCP `run` tool is the closest fit: `specs/design/mcp-server.md`
>   REQ-TOL-mcp-042 specifies a `stimuli` schedule applied at cycle start
>   and REQ-TOL-mcp-041 a per-cycle trace, which is exactly the shape of a
>   conformance trace, but `mcp/src/tools/run.rs:166` still rejects a
>   non-empty `stimuli` as not implemented.
> - The `ironplc_vm` crate already has everything needed:
>   `VmRunning::write_variable_raw`, `read_variable_raw`, and
>   `run_round(uptime_us, clock)` where the PLC time is caller-supplied; names
>   resolve through `DebugSection::program_variable`. The suite's harness
>   (`harness/ironplc`, ~300 lines) uses that and runs the 18 tests in well
>   under a second.
>
> So the question is not *whether* IronPLC can run such a suite (it can,
> today, through the crate) but *which public surface you would want it to
> use in CI*:
>
> (a) a `--trace FILE` option on `ironplcvm run` that reads the trace header
>     (period, program, inputs, outputs), replaces the wall clock by
>     `cycle * period`, writes the inputs before each `run_round`, and
>     renders the outputs with the existing `VariableRenderer`. About 150
>     lines in `vm-cli`, no VM change, and the suite becomes a shell script
>     like `tests/e2e/library/verify.sh`;
> (b) finishing REQ-TOL-mcp-042 (`stimuli`) so the suite runs through the
>     MCP server; or
> (c) keeping the harness as a crate in `compiler/` next to the
>     `codegen/tests/it/end_to_end_*.rs` step scripts, whose
>     `write`/`run`/`expect` form the trace format mirrors line for line.
>
> I have (c) working and would be glad to contribute (a) if you prefer a
> binary-only CI path.

## Replacement for the "where I can check" sentence

> I have run the same 18 traces against IronPLC (commit `5ea0610`),
> matiec/Beremiz's `iec2c` (commit `3a41303`) and RuSTy (commit `e911ee5`,
> stdlib built with its `mock_time` feature); see `notes/comparison.md` in
> the suite. The three runtimes pass 10, 10 and 8 of the 12 conformant tests
> and disagree with each other on timer edges, `F_TRIG` start-up, `SR`/`RS`
> input names and `CTU` above `PV`, which is what makes a shared suite worth
> having.

---

## Complete issue body (fallback if the draft is unavailable)

**Title:** Proposal: an open, runtime-agnostic IEC 61131-3 conformance trace suite (18 tests, CC0)

### What

A set of plain `.st` programs with plain-text expected I/O traces, one
record per scan cycle (inputs applied at cycle start, outputs sampled at
cycle end, simulated time `t = cycle * period`). No dependency on IronPLC:
the same files run against matiec and RuSTy. Twelve tests cover TON, TOF, TP,
R_TRIG, F_TRIG, SR/RS, CTU, IF/CASE, FOR+EXIT, WHILE/REPEAT, function calls
and a function block with two instances, scoped to BOOL/INT/DINT/UINT/TIME.
Six more record implementation-defined corners (INT overflow, division by
zero, operand evaluation order, TON with a changing PT, FOR bound modified
in the loop, CTU with PV = 0) as what IronPLC does today, with what the
standard says next to it. Expected values are derived by hand from the
standard's bodies and timing diagrams, with the derivation in each file, and
a small Lean 4 model proves the traces follow from those derivations.

### Why IronPLC might want it

Running the suite on `5ea0610` finds two timer behaviours that differ from
the standard's timing diagrams and from matiec (both in
`vm/src/intrinsic.rs`):

1. **TOF starts an off-delay at power-up although IN was never TRUE**: the
   first scan with IN = FALSE is taken as a falling edge (`else if !running`
   branch), so Q is TRUE for PT after start.
2. **TP retriggers while IN stays TRUE**: after the pulse ends, the next scan
   starts a new pulse (`else if in_val` with no edge detection), so a held IN
   produces a free-running oscillator of period PT + 1 cycle. Also, ET stays
   at PT after the pulse when IN is already FALSE.

Both have one-file reproducers and the actual output recorded in the suite.
Everything else in the twelve conformant tests passes.

### Open questions

1. Would you host it (under `tests/conformance/`?) or prefer it to live
   outside the repository and be referenced from a `specs/design/` document
   with `REQ-` ids, as the existing requirement-tagged tests are?
2. *(the rewritten question 2 above)*
3. For the implementation-defined corners, would you rather IronPLC's
   choices be documented (wrap on INT overflow, trap on division by zero,
   left-to-right evaluation, FOR bound re-read every iteration) or made
   explicit by compiler options?

*(the rewritten "where I can check" sentence above)*
