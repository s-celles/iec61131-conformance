# RuSTy harness

Runs the suite against RuSTy (PLC-lang/rusty), the LLVM-based ST compiler.

Requirements: a RuSTy checkout built with LLVM 21, and its standard library
built with the `mock_time` feature so that the timers read a clock the
driver can set:

```sh
git clone https://github.com/PLC-lang/rusty
cd rusty
export LLVM_SYS_211_PREFIX=/usr/lib/llvm-21 LLVM_CONFIG=/usr/lib/llvm-21/bin/llvm-config
cargo build --release                                   # target/release/plc
cargo build --release -p iec61131std --features mock_time   # target/release/libiec61131std.a
```

Then, from the suite root:

```sh
python3 -I harness/rusty/run.py --plc rusty/target/release/plc --rusty-src rusty conformance
```

How it works: each test is copied with `PROGRAM main` renamed to
`PROGRAM conf_prog` (a `main` symbol would clash with the C driver), ST
accessor functions `__set_<input>`, `__get_<output>` and `__run` are
appended, `plc -c` compiles it together with the stdlib `.st` declarations,
and a generated C driver calls the accessors and `__mock_time_set_ns` once
per trace record. `--record` prints what RuSTy produced in `.trace` record
syntax, `--keep` leaves the per-test build directory for inspection.
