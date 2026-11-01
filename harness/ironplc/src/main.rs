//! Runs every `<name>.st` + `<name>.trace` pair under a directory against the
//! IronPLC VM and reports pass/fail per cycle.
//!
//! Usage:
//!   conformance-ironplc [--ironplcc PATH] [--record] [--verbose] DIR_OR_FILE...
//!
//! `--record` prints, for each test, the record lines the VM actually
//! produced (same format as the .trace body) instead of comparing. It is how
//! the `conformance/undefined/*.trace` files were produced.
//!
//! Exit status: 0 when every conformant test passes (implementation-defined
//! traces never fail the run), 1 otherwise, 2 on a harness error.

mod trace;

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use ironplc_container::debug_format::VariableRenderer;
use ironplc_container::debug_section::{iec_type_tag, VarNameEntry};
use ironplc_container::Container;
use ironplc_vm::{Clock, Vm, VmBuffers};
use trace::{Expected, Status, Trace, Value};

/// A clock that never advances: task execution time is not under test and
/// a constant clock disables the watchdog (see ironplc `vm/src/clock.rs`).
struct FrozenClock;
impl Clock for FrozenClock {
    fn now_us(&mut self) -> u64 {
        0
    }
}

struct Options {
    ironplcc: PathBuf,
    record: bool,
    verbose: bool,
    paths: Vec<PathBuf>,
}

fn parse_args() -> Options {
    let mut o = Options {
        ironplcc: PathBuf::from("ironplcc"),
        record: false,
        verbose: false,
        paths: Vec::new(),
    };
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--ironplcc" => o.ironplcc = PathBuf::from(args.next().expect("--ironplcc PATH")),
            "--record" => o.record = true,
            "--verbose" | "-v" => o.verbose = true,
            _ => o.paths.push(PathBuf::from(a)),
        }
    }
    if o.paths.is_empty() {
        eprintln!("usage: conformance-ironplc [--ironplcc PATH] [--record] [-v] DIR_OR_FILE...");
        std::process::exit(2);
    }
    o
}

fn collect_tests(paths: &[PathBuf]) -> Vec<PathBuf> {
    let mut out = Vec::new();
    fn walk(p: &Path, out: &mut Vec<PathBuf>) {
        if p.is_dir() {
            let mut entries: Vec<_> = fs::read_dir(p).unwrap().flatten().map(|e| e.path()).collect();
            entries.sort();
            for e in entries {
                walk(&e, out);
            }
        } else if p.extension().map(|e| e == "st").unwrap_or(false) {
            out.push(p.to_path_buf());
        }
    }
    for p in paths {
        walk(p, &mut out);
    }
    out
}

/// Encodes a trace value into the VM's 64-bit slot for the variable's
/// declared type, as `Slot::from_i32`/`from_u32` would (signed values
/// sign-extended, unsigned zero-extended, BOOL 0/1, TIME i32 milliseconds).
fn encode(entry: &VarNameEntry, v: &Value) -> Result<u64, String> {
    let tag = entry.iec_type_tag;
    match (tag, v) {
        (iec_type_tag::BOOL, Value::Bool(b)) => Ok(*b as u64),
        (iec_type_tag::INT, Value::Int(i)) if (-32768..=32767).contains(i) => Ok(*i as u64),
        (iec_type_tag::DINT, Value::Int(i)) if (i32::MIN as i64..=i32::MAX as i64).contains(i) => {
            Ok(*i as u64)
        }
        (iec_type_tag::UINT, Value::Int(i)) if (0..=65535).contains(i) => Ok(*i as u64),
        (iec_type_tag::TIME, Value::Time(ms)) if (0..=i32::MAX as i64).contains(ms) => Ok(*ms as u64),
        (iec_type_tag::BYTE, Value::Bits { v, digits: 2 }) => Ok(*v),
        (iec_type_tag::WORD, Value::Bits { v, digits: 4 }) => Ok(*v),
        (iec_type_tag::DWORD, Value::Bits { v, digits: 8 }) => Ok(*v),
        _ => Err(format!(
            "cannot store {v} into {} : {} (type tag {tag})",
            entry.name, entry.type_name
        )),
    }
}

/// The value part of the `--dump-vars` rendering, e.g. `TRUE`, `-5`, `T#300ms`.
fn render(renderer: &VariableRenderer, entry: &VarNameEntry, raw: u64, data: &[u8]) -> String {
    let line = renderer.line(entry.var_index.raw(), raw, data);
    match line.split_once(": ") {
        Some((_, v)) => v.to_string(),
        None => line,
    }
}

enum Outcome {
    Pass,
    Fail(Vec<String>),
    /// implementation-defined trace that matched / differed
    Same,
    Differs(Vec<String>),
    Error(String),
}

fn run_test(st: &Path, opts: &Options) -> Outcome {
    let trace_path = st.with_extension("trace");
    let text = match fs::read_to_string(&trace_path) {
        Ok(t) => t,
        Err(e) => return Outcome::Error(format!("cannot read {}: {e}", trace_path.display())),
    };
    let trace: Trace = match trace::parse(&text) {
        Ok(t) => t,
        Err(e) => return Outcome::Error(format!("{}: {e}", trace_path.display())),
    };

    // Compile with the ironplcc CLI, so the harness tests the shipped
    // compiler and not an in-process build of it.
    let tmp = std::env::temp_dir().join(format!(
        "iec61131-conformance-{}-{}.iplc",
        std::process::id(),
        st.file_stem().unwrap().to_string_lossy()
    ));
    let out = match Command::new(&opts.ironplcc)
        .arg("compile")
        .arg("--output")
        .arg(&tmp)
        .arg(st)
        .output()
    {
        Ok(o) => o,
        Err(e) => return Outcome::Error(format!("cannot run {}: {e}", opts.ironplcc.display())),
    };
    if !out.status.success() {
        // A program the compiler rejects is a failed test, not a harness error:
        // every conformant program is valid IEC 61131-3.
        let msg = format!(
            "ironplcc failed to compile the program:\n{}{}",
            String::from_utf8_lossy(&out.stdout),
            String::from_utf8_lossy(&out.stderr)
        );
        return match trace.status {
            Status::Conformant => Outcome::Fail(vec![msg]),
            Status::ImplementationDefined => Outcome::Differs(vec![msg]),
        };
    }
    let bytes = fs::read(&tmp).expect("container written");
    let _ = fs::remove_file(&tmp);
    let container = match Container::read_from(&mut bytes.as_slice()) {
        Ok(c) => c,
        Err(e) => return Outcome::Error(format!("container read: {e}")),
    };
    let debug = match container.debug_section.as_ref() {
        Some(d) => d,
        None => return Outcome::Error("container has no debug section".into()),
    };
    let resolve = |name: &str| -> Result<VarNameEntry, String> {
        debug
            .program_variable(name)
            .cloned()
            .ok_or_else(|| format!("program declares no variable '{name}'"))
    };
    let inputs: Vec<VarNameEntry> = match trace.inputs.iter().map(|n| resolve(n)).collect() {
        Ok(v) => v,
        Err(e) => return Outcome::Error(e),
    };
    let outputs: Vec<VarNameEntry> = match trace.outputs.iter().map(|n| resolve(n)).collect() {
        Ok(v) => v,
        Err(e) => return Outcome::Error(e),
    };
    let renderer = VariableRenderer::new(&container);

    let mut bufs = VmBuffers::from_container(&container);
    let mut running = match Vm::new().load(&container, &mut bufs) {
        Ok(ready) => match ready.start() {
            Ok(r) => r,
            Err(ctx) => return Outcome::Error(format!("VM start trap: {}", ctx.trap)),
        },
        Err(trap) => return Outcome::Error(format!("VM load trap: {trap}")),
    };

    let mut clock = FrozenClock;
    let mut problems: Vec<String> = Vec::new();
    let mut recorded: Vec<String> = Vec::new();

    for rec in &trace.records {
        for (name, value) in &rec.inputs {
            let entry = &inputs[trace.inputs.iter().position(|n| n == name).unwrap()];
            match encode(entry, value) {
                Ok(raw) => {
                    if let Err(t) = running.write_variable_raw(entry.var_index, raw) {
                        return Outcome::Error(format!("write {name}: {t}"));
                    }
                }
                Err(e) => return Outcome::Error(format!("cycle {}: {e}", rec.cycle)),
            }
        }
        let uptime_us = rec.cycle * trace.period_ms * 1000;
        let scans_before = running.scan_count();
        let result = running.run_round(uptime_us, &mut clock);

        let input_part: String = rec
            .inputs
            .iter()
            .map(|(n, v)| format!(" {n}={v}"))
            .collect();

        match result {
            Err(ctx) => {
                let msg = format!("{}", ctx.trap);
                recorded.push(format!("{}{} => trap   # {msg}", rec.cycle, input_part));
                match &rec.expected {
                    Expected::Trap => {}
                    Expected::Outputs(_) => problems.push(format!(
                        "cycle {} (trace line {}): unexpected trap: {msg}",
                        rec.cycle, rec.line
                    )),
                }
                break;
            }
            Ok(()) => {
                if running.scan_count() == scans_before {
                    return Outcome::Error(format!(
                        "cycle {}: the VM ran no scan at t={uptime_us}us (is the program freewheeling?)",
                        rec.cycle
                    ));
                }
                let actual: Vec<(String, String)> = outputs
                    .iter()
                    .map(|e| {
                        let raw = running.read_variable_raw(e.var_index).unwrap_or(0);
                        (
                            e.name.to_ascii_lowercase(),
                            render(&renderer, e, raw, running.data_region()),
                        )
                    })
                    .collect();
                let out_part: String = actual.iter().map(|(n, v)| format!(" {n}={v}")).collect();
                recorded.push(format!("{}{} =>{}", rec.cycle, input_part, out_part));
                match &rec.expected {
                    Expected::Trap => problems.push(format!(
                        "cycle {} (trace line {}): expected a trap, VM completed the cycle with{}",
                        rec.cycle, rec.line, out_part
                    )),
                    Expected::Outputs(exp) => {
                        for (name, value) in exp {
                            if *value == Value::Any {
                                continue;
                            }
                            let got = &actual.iter().find(|(n, _)| n == name).unwrap().1;
                            if *got != value.to_string() {
                                problems.push(format!(
                                    "cycle {} (trace line {}): {name} expected {value}, got {got}",
                                    rec.cycle, rec.line
                                ));
                            }
                        }
                    }
                }
            }
        }
    }

    if opts.record {
        for l in &recorded {
            println!("{l}");
        }
    }
    match (trace.status, problems.is_empty()) {
        (Status::Conformant, true) => Outcome::Pass,
        (Status::Conformant, false) => Outcome::Fail(problems),
        (Status::ImplementationDefined, true) => Outcome::Same,
        (Status::ImplementationDefined, false) => Outcome::Differs(problems),
    }
}

fn main() {
    let opts = parse_args();
    let tests = collect_tests(&opts.paths);
    let (mut pass, mut fail, mut same, mut differs, mut errors) = (0, 0, 0, 0, 0);
    for st in &tests {
        let name = st.display();
        if opts.record {
            println!("### {name}");
        }
        match run_test(st, &opts) {
            Outcome::Pass => {
                pass += 1;
                println!("PASS    {name}");
            }
            Outcome::Same => {
                same += 1;
                println!("SAME    {name} (implementation-defined)");
            }
            Outcome::Fail(p) => {
                fail += 1;
                println!("FAIL    {name}");
                for l in p {
                    println!("        {l}");
                }
            }
            Outcome::Differs(p) => {
                differs += 1;
                println!("DIFFERS {name} (implementation-defined)");
                for l in p {
                    println!("        {l}");
                }
            }
            Outcome::Error(e) => {
                errors += 1;
                println!("ERROR   {name}: {e}");
            }
        }
        if opts.verbose {
            println!();
        }
    }
    println!(
        "\n{} tests: {pass} pass, {fail} fail, {same} same, {differs} differs, {errors} error",
        tests.len()
    );
    if fail > 0 || errors > 0 {
        std::process::exit(1);
    }
}
