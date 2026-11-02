//! Runs every `<name>.st` + `<name>.trace` pair under a directory against rk
//! (github.com/adclz/rk), an IEC 61131-3 Structured Text compiler that emits
//! one WebAssembly core module per workspace.
//!
//! Usage:
//!   conformance-rk [--rk PATH] [--record] DIR_OR_FILE...
//!
//! For each test the harness makes an rk workspace (`config.toml` and
//! `src/main.st`), runs `rk compile`, and hosts the resulting `core.wasm`:
//!
//! - `env.memory` is a linear memory of the size the module asks for;
//! - the WASI monotonic clock returns the simulated time `cycle * period_ms`
//!   (the wall clock and the zone answer the epoch and 0, nothing in the suite
//!   reads them);
//! - `__init` runs once, then for each record the inputs are written, the
//!   tasks due at that instant run in the order of the `rk.schedule` section
//!   (rk's contract: "dispatch order, most urgent first; a consumer runs the
//!   due tasks in slice order"), and the outputs are read;
//! - variables are resolved by name through rk's `debug-symbols`.
//!
//! A test without a CONFIGURATION (SPEC.md version 1) gets one appended: one
//! task of interval `period_ms` running one instance `P` of the program, so
//! `x` in the trace is `P.x` in the module. A wasm trap or an uncaught
//! WebAssembly exception (rk's bounds checks raise one) is a `trap` record.
//!
//! Exit status: 0 when every conformant test passes, 1 otherwise, 2 on a
//! usage error.

#[path = "../../ironplc/src/trace.rs"]
mod trace;

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicI64, Ordering};
use std::sync::Arc;

use debug_format::info::{DebugInfo, VarLoc, VarValue};
use debug_format::{ScheduleManifest, SymType, SCHEDULE_SECTION};
use trace::{Expected, Status, Trace, Value};
use wasmtime::{Caller, Config, Engine, ExternType, Linker, Memory, MemoryType, Module, Store};

/// The namespaces of rk's standard library that hold IEC 61131-3 standard
/// functions and function blocks.
const STD_USING: &str = "USING Std.Math; USING Std.Strings; USING Std.Convert; USING Std.Selection; \
USING Std.Timers; USING Std.Counters; USING Std.Edge; USING Std.Bistable; USING Std.Bits; USING Std.Memory;";

/// Instructions one task call may execute before the harness calls it a hang.
const FUEL_PER_CALL: u64 = 2_000_000_000;

struct Options {
    rk: PathBuf,
    record: bool,
    paths: Vec<PathBuf>,
}

fn parse_args() -> Options {
    let mut o = Options { rk: PathBuf::from("rk"), record: false, paths: Vec::new() };
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--rk" => o.rk = PathBuf::from(args.next().expect("--rk PATH")),
            "--record" => o.record = true,
            _ => o.paths.push(PathBuf::from(a)),
        }
    }
    if o.paths.is_empty() {
        eprintln!("usage: conformance-rk [--rk PATH] [--record] DIR_OR_FILE...");
        std::process::exit(2);
    }
    o
}

fn collect_tests(paths: &[PathBuf]) -> Vec<PathBuf> {
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
    let mut out = Vec::new();
    for p in paths {
        walk(p, &mut out);
    }
    out
}

/// Whether the source declares its own CONFIGURATION (SPEC.md version 2).
fn has_configuration(st: &str) -> bool {
    st.lines().any(|l| {
        let t = l.trim_start();
        t.len() >= 13 && t[..13].eq_ignore_ascii_case("CONFIGURATION")
    })
}

enum Outcome {
    Pass,
    Fail(Vec<String>),
    Same,
    Differs(Vec<String>),
    Error(String),
}

/// A trace value as the `VarValue` rk's encoder takes for a variable of type `ty`.
fn to_var_value(ty: SymType, v: &Value) -> Result<VarValue, String> {
    let int = |lo: i64, hi: i64, i: i64| -> Result<i64, String> {
        if (lo..=hi).contains(&i) { Ok(i) } else { Err(format!("{i} is out of range for {}", ty.rk_name())) }
    };
    Ok(match (ty, v) {
        (SymType::Bool, Value::Bool(b)) => VarValue::Bool(*b),
        (SymType::SInt, Value::Int(i)) => VarValue::I8(int(-128, 127, *i)? as i8),
        (SymType::Int, Value::Int(i)) => VarValue::I16(int(-32768, 32767, *i)? as i16),
        (SymType::DInt, Value::Int(i)) => VarValue::I32(int(i32::MIN as i64, i32::MAX as i64, *i)? as i32),
        (SymType::LInt, Value::Int(i)) => VarValue::I64(*i),
        (SymType::USInt, Value::Int(i)) => VarValue::U8(int(0, 255, *i)? as u8),
        (SymType::UInt, Value::Int(i)) => VarValue::U16(int(0, 65535, *i)? as u16),
        (SymType::UDInt, Value::Int(i)) => VarValue::U32(int(0, u32::MAX as i64, *i)? as u32),
        (SymType::ULInt, Value::Int(i)) => VarValue::U64(int(0, i64::MAX, *i)? as u64),
        (SymType::Byte, Value::Bits { v, digits: 2 }) => VarValue::U8(*v as u8),
        (SymType::Word, Value::Bits { v, digits: 4 }) => VarValue::U16(*v as u16),
        (SymType::DWord, Value::Bits { v, digits: 8 }) => VarValue::U32(*v as u32),
        (SymType::Real, Value::Real { v, .. }) => VarValue::F32(*v as f32),
        (SymType::LReal, Value::Real { v, .. }) => VarValue::F64(*v),
        (SymType::Time, Value::Time(ms)) => VarValue::I32(int(0, i32::MAX as i64, *ms)? as i32),
        (SymType::LTime, Value::Time(ms)) => VarValue::I64(ms * 1_000_000),
        _ => return Err(format!("cannot store {v} into a {}", ty.rk_name())),
    })
}

/// The trace rendering of a value read back: `TRUE`, `-5`, `16#0F`, `T#300ms`, `'abc'`.
fn render(ty: SymType, v: &VarValue) -> String {
    match (ty, v) {
        (_, VarValue::Bool(b)) => if *b { "TRUE".into() } else { "FALSE".into() },
        (SymType::Byte, VarValue::U8(x)) => format!("16#{x:02X}"),
        (SymType::Word, VarValue::U16(x)) => format!("16#{x:04X}"),
        (SymType::DWord, VarValue::U32(x)) => format!("16#{x:08X}"),
        (SymType::LWord, VarValue::U64(x)) => format!("16#{x:016X}"),
        (SymType::Time, VarValue::I32(ms)) => format!("T#{ms}ms"),
        (SymType::LTime, VarValue::I64(ns)) => format!("T#{}ms", ns / 1_000_000),
        (_, VarValue::I8(x)) => x.to_string(),
        (_, VarValue::I16(x)) => x.to_string(),
        (_, VarValue::I32(x)) => x.to_string(),
        (_, VarValue::I64(x)) => x.to_string(),
        (_, VarValue::U8(x)) => x.to_string(),
        (_, VarValue::U16(x)) => x.to_string(),
        (_, VarValue::U32(x)) => x.to_string(),
        (_, VarValue::U64(x)) => x.to_string(),
        (_, VarValue::F32(x)) => real(*x as f64, true),
        (_, VarValue::F64(x)) => real(*x, false),
        (_, VarValue::String(s)) => trace::encode_string_literal(s.as_bytes()),
        (_, VarValue::Enum { raw, .. }) => raw.to_string(),
        (_, VarValue::Unavailable(why)) => format!("<unavailable: {why}>"),
    }
}

/// A REAL / LREAL as SPEC.md writes it: a decimal with a `.`, `inf`, `-inf`, `nan`.
fn real(x: f64, single: bool) -> String {
    if x.is_nan() {
        return "nan".into();
    }
    if x.is_infinite() {
        return if x > 0.0 { "inf".into() } else { "-inf".into() };
    }
    let s = if single { format!("{}", x as f32) } else { format!("{x}") };
    if s.contains('.') || s.contains('e') || s.contains('E') { s } else { format!("{s}.0") }
}

/// The text of a trap or of an uncaught WebAssembly exception.
fn trap_words(err: &wasmtime::Error) -> String {
    if let Some(trap) = err.downcast_ref::<wasmtime::Trap>() {
        let w = trap.to_string();
        return w.strip_prefix("wasm trap: ").map(str::to_string).unwrap_or(w);
    }
    err.root_cause().to_string().lines().next().unwrap_or("").to_string()
}

fn custom_section<'a>(wasm: &'a [u8], name: &str) -> Option<&'a [u8]> {
    for payload in wasmparser::Parser::new(0).parse_all(wasm) {
        if let Ok(wasmparser::Payload::CustomSection(r)) = payload {
            if r.name() == name {
                return Some(r.data());
            }
        }
    }
    None
}

/// Diagnostics point into the stdlib copy rk writes in the user's cache
/// (`file:///…/rk/p/<64 hex>/Strings.st`), a path that differs per machine:
/// written `<rk-stdlib>/Strings.st` instead.
fn mask_stdlib_cache(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut rest = s;
    while let Some(i) = rest.find("file://") {
        let tail = &rest[i..];
        let end = tail.find(|c: char| c.is_whitespace()).unwrap_or(tail.len());
        let url = &tail[..end];
        let masked = url.find("/rk/p/").and_then(|j| {
            let after = &url[j + 6..];
            let hex = after.split('/').next()?;
            (hex.len() == 64 && hex.bytes().all(|b| b.is_ascii_hexdigit()))
                .then(|| format!("<rk-stdlib>{}", &after[64..]))
        });
        out.push_str(&rest[..i]);
        out.push_str(masked.as_deref().unwrap_or(url));
        rest = &tail[end..];
    }
    out.push_str(rest);
    out
}

fn compile(st: &Path, st_text: &str, trace: &Trace, rk: &Path) -> Result<Result<Vec<u8>, String>, String> {
    let dir = std::env::temp_dir().join(format!(
        "rk-conformance-{}-{}",
        std::process::id(),
        st.file_stem().unwrap().to_string_lossy()
    ));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(dir.join("src")).map_err(|e| format!("creating {}: {e}", dir.display()))?;
    fs::write(dir.join("config.toml"), "[project]\nname = \"conformance\"\nversion = \"0.1\"\n")
        .map_err(|e| e.to_string())?;
    // rk keeps the IEC standard functions and blocks in namespaces (TON in
    // Std.Timers, LEN in Std.Strings, ...); a user imports them with USING,
    // and so does the harness, on one line so the diagnostics' line numbers
    // are off by one only. A POU of the program still wins over an imported
    // one (docs/namespaces.md).
    let mut src = format!("{STD_USING}\n{st_text}");
    if !has_configuration(st_text) {
        src.push_str(&format!(
            "\nCONFIGURATION ConformanceConf\n  RESOURCE Res ON CPU\n    \
             TASK ConformanceTask(INTERVAL := T#{}ms, PRIORITY := 0);\n    \
             PROGRAM P WITH ConformanceTask : {};\n  END_RESOURCE\nEND_CONFIGURATION\n",
            trace.period_ms, trace.program
        ));
    }
    fs::write(dir.join("src").join("main.st"), src).map_err(|e| e.to_string())?;
    let out = Command::new(rk)
        .arg("compile")
        .current_dir(&dir)
        .env("NO_COLOR", "1")
        .output()
        .map_err(|e| format!("cannot run {}: {e}", rk.display()))?;
    let wasm = dir.join("rk_build").join("debug").join("core.wasm");
    let result = if out.status.success() && wasm.exists() {
        Ok(fs::read(&wasm).map_err(|e| e.to_string())?)
    } else {
        Err(format!(
            "rk failed to compile the program:\n{}{}",
            String::from_utf8_lossy(&out.stdout),
            String::from_utf8_lossy(&out.stderr)
        )
        .replace(&format!("{}/", dir.display()), "<tmpdir>/"))
        .map_err(|m| mask_stdlib_cache(&m))
    };
    let _ = fs::remove_dir_all(&dir);
    Ok(result)
}

fn run_test(st: &Path, opts: &Options, recorded: &mut Vec<String>) -> Outcome {
    let trace_path = st.with_extension("trace");
    let text = match fs::read_to_string(&trace_path) {
        Ok(t) => t,
        Err(e) => return Outcome::Error(format!("cannot read {}: {e}", trace_path.display())),
    };
    let trace = match trace::parse(&text) {
        Ok(t) => t,
        Err(e) => return Outcome::Error(format!("{}: {e}", trace_path.display())),
    };
    let st_text = match fs::read_to_string(st) {
        Ok(t) => t,
        Err(e) => return Outcome::Error(format!("cannot read {}: {e}", st.display())),
    };
    let failed = |msg: String| match trace.status {
        Status::Conformant => Outcome::Fail(vec![msg]),
        Status::ImplementationDefined => Outcome::Differs(vec![msg]),
    };
    let wasm = match compile(st, &st_text, &trace, &opts.rk) {
        Err(e) => return Outcome::Error(e),
        Ok(Err(msg)) => return failed(msg),
        Ok(Ok(w)) => w,
    };

    let schedule = match custom_section(&wasm, SCHEDULE_SECTION).map(ScheduleManifest::from_msgpack) {
        Some(Ok(s)) => s,
        Some(Err(e)) => return Outcome::Error(format!("{SCHEDULE_SECTION}: {e}")),
        None => return Outcome::Error(format!("the module has no {SCHEDULE_SECTION} section")),
    };
    let debug = DebugInfo::from_wasm(&wasm);
    let v2 = has_configuration(&st_text);
    let path_of = |name: &str| if v2 { name.to_string() } else { format!("P.{name}") };
    let resolve = |name: &str| -> Result<VarLoc, String> {
        debug.resolve(&path_of(name)).ok_or_else(|| {
            let known: Vec<&str> = debug.list_symbols().iter().map(|s| s.path.as_str()).take(30).collect();
            format!("no symbol '{}' in the module (it has: {})", path_of(name), known.join(", "))
        })
    };
    let inputs: Vec<VarLoc> = match trace.inputs.iter().map(|n| resolve(n)).collect() {
        Ok(v) => v,
        Err(e) => return Outcome::Error(e),
    };
    let outputs: Vec<VarLoc> = match trace.outputs.iter().map(|n| resolve(n)).collect() {
        Ok(v) => v,
        Err(e) => return Outcome::Error(e),
    };

    // ---- host ----
    let mut config = Config::new();
    config.wasm_exceptions(true);
    config.consume_fuel(true);
    let engine = match Engine::new(&config) {
        Ok(e) => e,
        Err(e) => return Outcome::Error(format!("wasm engine: {e}")),
    };
    let module = match Module::new(&engine, &wasm) {
        Ok(m) => m,
        Err(e) => return Outcome::Error(format!("loading core.wasm: {e}")),
    };
    let mut store = Store::new(&engine, ());
    let min_pages = module.imports().find_map(|i| match i.ty() {
        ExternType::Memory(mt) => Some(mt.minimum()),
        _ => None,
    });
    let Some(min_pages) = min_pages else {
        return Outcome::Error("the module imports no env.memory".into());
    };
    let memory = match Memory::new(&mut store, MemoryType::new(min_pages as u32, None)) {
        Ok(m) => m,
        Err(e) => return Outcome::Error(format!("memory: {e}")),
    };
    let now_ns = Arc::new(AtomicI64::new(0));
    let mut linker: Linker<()> = Linker::new(&engine);
    if let Err(e) = linker.define(&store, "env", "memory", memory) {
        return Outcome::Error(format!("env.memory: {e}"));
    }
    for import in module.imports() {
        let (m, n) = (import.module().to_string(), import.name().to_string());
        let r = if n == "now" && m.contains("monotonic-clock") {
            let clock = now_ns.clone();
            linker.func_wrap(&m, &n, move || clock.load(Ordering::SeqCst)).map(|_| ())
        } else if n == "now" && m.contains("wall-clock") {
            linker
                .func_wrap(&m, &n, move |mut caller: Caller<'_, ()>, at: i32| -> wasmtime::Result<()> {
                    memory.write(&mut caller, at as usize, &[0u8; 16]).map_err(wasmtime::Error::msg)
                })
                .map(|_| ())
        } else if n == "utc-offset" && m.contains("timezone") {
            linker.func_wrap(&m, &n, |_s: i64, _ns: i32| -> i32 { 0 }).map(|_| ())
        } else {
            Ok(())
        };
        if let Err(e) = r {
            return Outcome::Error(format!("wiring {m}.{n}: {e}"));
        }
    }
    if let Err(e) = linker.define_unknown_imports_as_traps(&module) {
        return Outcome::Error(format!("stubbing imports: {e}"));
    }
    let _ = store.set_fuel(FUEL_PER_CALL);
    let instance = match linker.instantiate(&mut store, &module) {
        Ok(i) => i,
        Err(e) => return Outcome::Error(format!("instantiating core.wasm: {}", trap_words(&e))),
    };
    if let Ok(init) = instance.get_typed_func::<(), ()>(&mut store, "__init") {
        let _ = store.set_fuel(FUEL_PER_CALL);
        if let Err(e) = init.call(&mut store, ()) {
            return Outcome::Error(format!("__init: {}", trap_words(&e)));
        }
    }
    let mut tasks = Vec::new();
    for task in &schedule.tasks {
        let mut bodies = Vec::new();
        for p in &task.programs {
            match instance.get_typed_func::<i32, ()>(&mut store, &p.export) {
                Ok(f) => bodies.push((f, p.instance_addr as i32)),
                Err(e) => return Outcome::Error(format!("export {}: {e}", p.export)),
            }
        }
        tasks.push((task.period_ticks.max(1), bodies));
    }
    let tick_ns = schedule.common_ticktime_ns.max(1) as i64;

    // ---- cycles ----
    let mut problems = Vec::new();
    for rec in &trace.records {
        for (name, value) in &rec.inputs {
            let loc = &inputs[trace.inputs.iter().position(|n| n == name).unwrap()];
            let encoded = to_var_value(loc.ty, value).and_then(|vv| {
                let current = memory.data(&store)[loc.address as usize..(loc.address + loc.size) as usize].to_vec();
                loc.encode(&current, vv).map_err(|e| e.to_string())
            });
            match encoded {
                Ok(bytes) => {
                    if let Err(e) = memory.write(&mut store, loc.address as usize, &bytes) {
                        return Outcome::Error(format!("writing {name}: {e}"));
                    }
                }
                Err(e) => return Outcome::Error(format!("cycle {}: {name}: {e}", rec.cycle)),
            }
        }
        let t_ns = (rec.cycle * trace.period_ms) as i64 * 1_000_000;
        now_ns.store(t_ns, Ordering::SeqCst);
        let mut trapped = None;
        if t_ns % tick_ns == 0 {
            let tick = (t_ns / tick_ns) as u64;
            'tasks: for (period, bodies) in &tasks {
                if tick % period != 0 {
                    continue;
                }
                for (body, this) in bodies {
                    let _ = store.set_fuel(FUEL_PER_CALL);
                    if let Err(e) = body.call(&mut store, *this) {
                        trapped = Some(trap_words(&e));
                        break 'tasks;
                    }
                }
            }
        }
        let input_part: String = rec.inputs.iter().map(|(n, v)| format!(" {n}={v}")).collect();
        if let Some(msg) = trapped {
            recorded.push(format!("{}{} => trap   # {msg}", rec.cycle, input_part));
            if let Expected::Outputs(_) = rec.expected {
                problems.push(format!("cycle {} (trace line {}): unexpected trap: {msg}", rec.cycle, rec.line));
            }
            break;
        }
        let data = memory.data(&store);
        let actual: Vec<(String, String)> = outputs
            .iter()
            .zip(trace.outputs.iter())
            .map(|(loc, name)| {
                let bytes = &data[loc.address as usize..(loc.address + loc.size) as usize];
                (name.clone(), render(loc.ty, &loc.decode(bytes)))
            })
            .collect();
        let out_part: String = actual.iter().map(|(n, v)| format!(" {n}={v}")).collect();
        recorded.push(format!("{}{} =>{}", rec.cycle, input_part, out_part));
        match &rec.expected {
            Expected::Trap => problems.push(format!(
                "cycle {} (trace line {}): expected a trap, got{}",
                rec.cycle, rec.line, out_part
            )),
            Expected::Outputs(exp) => {
                for (name, value) in exp {
                    if *value == Value::Any {
                        continue;
                    }
                    let idx = trace.outputs.iter().position(|n| n == name).unwrap();
                    let got = &actual[idx].1;
                    if !value.matches(got, outputs[idx].ty == SymType::LReal) {
                        problems.push(format!(
                            "cycle {} (trace line {}): {name} expected {value}, got {got}",
                            rec.cycle, rec.line
                        ));
                    }
                }
            }
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
        let mut recorded = Vec::new();
        let outcome = run_test(st, &opts, &mut recorded);
        if opts.record {
            println!("### {name}");
            for l in &recorded {
                println!("{l}");
            }
        }
        match outcome {
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
                    println!("        {}", l.replace('\n', "\n        "));
                }
            }
            Outcome::Differs(p) => {
                differs += 1;
                println!("DIFFERS {name} (implementation-defined)");
                for l in p {
                    println!("        {}", l.replace('\n', "\n        "));
                }
            }
            Outcome::Error(e) => {
                errors += 1;
                println!("ERROR   {name}: {e}");
            }
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
