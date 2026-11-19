# truST harness

Runs the suite against truST (johannesPettersson80/trust-platform), an IEC 61131-3
Structured Text toolchain and runtime that compiles programs to native code.

Requirements: a truST checkout, with the Rust toolchain its `rust-toolchain.toml`
pins (rustup installs it on the first build). Build the conformance driver, an
example of the `trust-runtime` crate, and truST's native toolchain folder, which
holds the program library the driver compiles each test against:

```sh
git clone https://github.com/johannesPettersson80/trust-platform trust
cd trust
cargo build --release -p trust-runtime --example conformance_driver   # target/release/examples/conformance_driver
bash scripts/native/build_toolchain_libraries.sh "$PWD/toolchain" x86_64-unknown-linux-gnu
```

Then, from the suite root:

```sh
python3 -I harness/trust/run.py --driver trust/target/release/examples/conformance_driver \
    --toolchain trust/toolchain --record conformance
```

How it works: for each test, `run.py` starts the driver with the `.st`, the
trace's `period_ms` and its output names, and writes the records' inputs to its
standard input, one record per line. The driver compiles the program with truST's
test harness (the same build the runtime runs), starts it with its declared initial
values, prints the outputs' declared types once, and for each record writes the
inputs, runs exactly one scan at PLC time `cycle * period_ms` and prints the
outputs in `.trace` record syntax; a scan that faults prints `trap: <fault>`. A
`CONFIGURATION` (SPEC.md version 2) runs with its own tasks. `run.py` compares
with the shared `harness/matiec/tracefmt.py`, so REAL/LREAL tolerances and string
escapes are the same as for the other runtimes. `--record` prints what truST
produced in `.trace` record syntax.

A program that does not compile is a FAIL of a conformant test with truST's
errors; a driver refusal (an input type the trace syntax has no form for, a name
the program does not have) is an ERROR of that test.
