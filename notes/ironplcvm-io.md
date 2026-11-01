# How ironplcvm is driven from outside

IronPLC commit studied: `5ea0610a0620dd84e5864c96ecb805001d88bc4d` (2026-10-31),
workspace version 0.251.0. All paths below are relative to `compiler/` in the
IronPLC repository.

Build commands used:

```sh
git clone --depth 1 https://github.com/ironplc/ironplc
cd ironplc/compiler
cargo build --release -p ironplcc -p ironplcvm
```

## Summary

- The `ironplcvm run` CLI cannot inject inputs: it has no flag, no config file
  and no stdin protocol for writing a variable. It can only read the final
  variable image (`--dump-vars`) after `--scans N` rounds of wall-clock time.
- The debug server `ironplcvmd` (DAP) refuses `setVariable` and `evaluate`.
- The MCP server's `run` tool has a **specified** stimulus schedule
  (`stimuli[].time_ms` + `set{name: value}`, REQ-TOL-mcp-042) and returns a
  per-cycle trace (REQ-TOL-mcp-041), but the stimuli part is **not
  implemented** on this commit: `mcp/src/tools/run.rs:166` rejects any
  non-empty `stimuli` with "not yet implemented".
- The library crate `ironplc_vm` does everything needed: `VmRunning::write_variable_raw`,
  `VmRunning::read_variable_raw`, and `VmRunning::run_round(uptime_us, clock)`
  where **simulated time is a caller argument**. That is the path the harness
  uses. No change to IronPLC is required for the suite.

## 1. The CLI: `ironplcvm run`

File: `vm-cli/src/cli.rs`, function `run(path, dump_vars, scans)`.

- Loads the `.iplc` container (`ironplc_container::Container::read_from`),
  builds `VmBuffers::from_container`, then `Vm::new().load(..).start()`.
- Loop: `running.run_round(uptime_us, &mut execution_clock)` with
  `uptime_us = start.elapsed()` (real wall clock, `std::time::Instant`), then
  sleeps until `running.next_due_us()`.
- `--scans N` stops after N scheduling rounds (not necessarily N executions of
  a cyclic task).
- `--dump-vars FILE|-` writes every variable slot after the stop (or after a
  trap), one `NAME: VALUE` line each, rendered by
  `ironplc_container::debug_format::VariableRenderer::line` (TIME as
  `T#1500ms`, BOOL as `TRUE`/`FALSE`, integers in decimal). Function block
  instances are rendered as `<TON>`, their fields are not dumped.
- There is no input path at all. Documentation: `docs/reference/runtime/ironplcvm.rst`.

Consequence for a conformance run: a freewheeling program (no
`CONFIGURATION`) is run by the CLI against wall-clock time, so timer tests are
not reproducible through the CLI; and without inputs only "constant stimulus"
programs can be tested. The CLI is therefore unusable for this suite except as
a smoke check.

## 2. The debug server: `ironplcvmd`

File: `vm-cli/src/dap/` (entry `vm-cli/src/dap_main.rs`); docs
`docs/reference/runtime/ironplcvmd.rst`. The DAP server accepts
`freewheelingIntervalMs` and `scanLimit`, runs under simulated time, and
exposes `variables` for reading, but `setVariable`, `evaluate`, `pause` and
`restart` are "recognized but always refused". No input injection.

## 3. The MCP server: `run` tool

Files: `mcp/src/tools/run.rs` (tool input), `mcp/src/runner.rs` (`execute`),
spec `specs/design/mcp-server.md` (REQ-TOL-mcp-040 to 049).

What exists today:

- `execute(cached, trace_set, duration_ms, freewheeling_interval, limits)`
  drives `VmRunning::run_round` with a **simulated** `uptime_us` advanced by
  `next_due_us()`. A freewheeling task is rewritten into a cyclic one with the
  caller's `freewheeling_interval_ms` (`vm/src/freewheeling.rs`,
  `resolve_cycle_time`); the tool refuses to run without that value.
- The trace (`TraceSample { time_ms, task, variables: Vec<(name, value)> }`) is
  sampled **after** each cycle, with values rendered as JSON per
  REQ-TOL-mcp-043 (`BOOL` → boolean, integers → number, `TIME` → `"T#500ms"`).
- Variables are named fully qualified (`Main.Start`), resolved against the
  container debug section (`mcp/src/tools/pou_scope.rs`).

What does not exist: `run.rs:166` returns a diagnostic when `stimuli` is
non-empty. The spec says a stimulus is applied "at the start of the first scan
cycle whose simulated start time is >= time_ms", and persists until overwritten.
That is exactly the input-image semantics the conformance trace format needs,
so the format in `SPEC.md` is designed to map 1:1 onto a future `stimuli` +
`every_cycle` trace.

## 4. The library API (used by the harness)

Crate `ironplc_vm` (`vm/src/vm.rs`):

| Need | Function |
|---|---|
| Load | `Vm::new().load(&container, &mut VmBuffers::from_container(&container)) -> VmReady` |
| Start | `VmReady::start() -> Result<VmRunning, FaultContext>` (runs init functions) |
| Set an input | `VmRunning::write_variable_raw(VarIndex, u64)` (also `write_variable(VarIndex, i32)`) |
| Run one cycle at simulated time | `VmRunning::run_round(uptime_us: u64, clock: &mut impl Clock)` |
| Read an output | `VmRunning::read_variable_raw(VarIndex) -> u64` |
| Trap handling | `Err(FaultContext)` → `VmRunning::fault(ctx) -> VmFaulted`, `VmFaulted::trap()` |

- `uptime_us` is the PLC time and is **entirely caller-supplied** ("which it may
  simulate", doc comment on `run_round`). Timer intrinsics (`vm/src/intrinsic.rs`,
  `ton`/`tof`/`tp`) receive it as `cycle_time` and compute
  `elapsed_ms = (cycle_time - start_time) / 1000`.
- The `Clock` argument (`vm/src/clock.rs`) only measures task execution for the
  watchdog; a constant clock disables the watchdog, which is fine for tests.
- For a program with no `CONFIGURATION`, the compiler synthesizes one
  freewheeling task (`TaskType::Freewheeling`, `vm/src/scheduler.rs:55`), which
  is ready on every round. So "one `run_round` call = one scan", and the harness
  passes `uptime_us = cycle_index * period_ms * 1000`.
- Variable names → slots: the container debug section,
  `container/src/program_variables.rs`:
  `DebugSection::program_variable(name) -> Option<&VarNameEntry>` (case
  insensitive, program-scope and globals only). `VarNameEntry` carries
  `var_index`, `iec_type_tag` (`debug_section::iec_type_tag::{BOOL, INT, DINT,
  UINT, TIME, ...}`) and `type_name`. `ironplcc compile` writes the debug
  section by default.
- Slot encoding (`vm/src/value.rs`, `Slot`): signed integers are stored
  sign-extended to 64 bits (`Slot::from_i32`), unsigned zero-extended, BOOL as
  0/1, TIME as i32 milliseconds. The harness encodes/decodes exactly as
  `codegen/tests/it/common/slot_value.rs` does.

## 5. Existing integration / golden tests and their conventions

- `codegen/tests/it/end_to_end_*.rs` are the maintainers' end-to-end tests:
  ST source as a Rust string constant, compiled and run on every backend, then
  driven by a **step script** of `write("name", value)`, `run(uptime_us)`,
  `expect("name", value)` (`codegen/tests/it/common/{session.rs,backend.rs}`),
  e.g. `end_to_end_fb_ton.rs` case `in_reset_restarts`. This is the closest
  thing to a per-cycle I/O trace in the repository, and the trace format in
  `SPEC.md` is a line-oriented transcription of it: write inputs, run one
  cycle at time t, expect outputs.
- `vm/tests/it/execute_fb_*.rs` drive the VM with hand-built bytecode
  (`test_support::timer_test_container`), `write_variable` + `run_round(us)`.
- `tests/e2e/library/verify.sh` is the only shell-level golden test: compile
  with `ironplcc compile --output x.iplc file.st`, run
  `ironplcvm run x.iplc --scans 1 --dump-vars -`, `grep` the dump.
- Requirement-tagged tests (`#[spec_test(REQ_...)]`, `specs/design/*.md`) are
  the project's own conformance tracking; a new suite would naturally be
  referenced from a `specs/design/` document with `REQ-` ids.
- No `.st` + expected-output golden directory exists; `resources/test/*.st`
  are parser/analyzer fixtures without expected runtime output.

## 6. Smallest change that would let the CLI do this (patch description, not a PR)

Not needed for the harness (the library API suffices), but for a
runtime-agnostic CI that only has binaries:

1. In `vm-cli/src/cli.rs`, add to `run` two options: `--trace FILE` (a `.trace`
   file per `SPEC.md`) and `--trace-out FILE`. When `--trace` is given:
   - resolve each header variable with `DebugSection::program_variable`;
   - replace the wall-clock `uptime_us` by `cycle * period_ms * 1000` read
     from the trace header (freewheeling tasks rewritten through the existing
     `freewheeling::resolve_cycle_time`);
   - before each `run_round`, `write_variable_raw` every input of that cycle
     (encode with the `iec_type_tag` as `codegen/tests/it/common/slot_value.rs`);
   - after each `run_round`, render the outputs with the existing
     `VariableRenderer` and write one record line.
   That is about 150 lines, all in `vm-cli`, no VM change.
2. Alternatively, finish REQ-TOL-mcp-042 (`stimuli`) in `mcp/src/runner.rs`:
   before `run_round`, apply every stimulus whose `time_ms <= uptime_us/1000`
   via `write_variable_raw`. The conformance trace then converts to one MCP
   `run` call per test.
