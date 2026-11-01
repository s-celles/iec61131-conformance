//! Parser for the `.trace` format described in SPEC.md.
//!
//! Deliberately dependency-free and small, so it can be copied into another
//! runtime's harness.

use std::collections::BTreeMap;
use std::fmt;

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Value {
    Bool(bool),
    Int(i64),
    /// Milliseconds.
    Time(i64),
    /// `?`: not checked.
    Any,
}

impl Value {
    pub fn parse(s: &str) -> Result<Value, String> {
        if s == "?" {
            return Ok(Value::Any);
        }
        if s == "TRUE" {
            return Ok(Value::Bool(true));
        }
        if s == "FALSE" {
            return Ok(Value::Bool(false));
        }
        if let Some(rest) = s.strip_prefix("T#") {
            let digits = rest
                .strip_suffix("ms")
                .ok_or_else(|| format!("TIME literal must be T#<n>ms: {s}"))?;
            let ms: i64 = digits
                .parse()
                .map_err(|_| format!("bad TIME literal: {s}"))?;
            return Ok(Value::Time(ms));
        }
        s.parse::<i64>()
            .map(Value::Int)
            .map_err(|_| format!("bad value: {s}"))
    }
}

impl fmt::Display for Value {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Value::Bool(true) => write!(f, "TRUE"),
            Value::Bool(false) => write!(f, "FALSE"),
            Value::Int(i) => write!(f, "{i}"),
            Value::Time(ms) => write!(f, "T#{ms}ms"),
            Value::Any => write!(f, "?"),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Expected {
    Outputs(Vec<(String, Value)>),
    Trap,
}

#[derive(Clone, Debug)]
pub struct Record {
    pub cycle: u64,
    pub inputs: Vec<(String, Value)>,
    pub expected: Expected,
    pub line: usize,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Status {
    Conformant,
    ImplementationDefined,
}

#[derive(Clone, Debug)]
pub struct Trace {
    pub period_ms: u64,
    pub program: String,
    pub inputs: Vec<String>,
    pub outputs: Vec<String>,
    pub status: Status,
    pub reference: Option<String>,
    pub records: Vec<Record>,
}

fn split_assign(tok: &str, line: usize) -> Result<(String, Value), String> {
    let (name, value) = tok
        .split_once('=')
        .ok_or_else(|| format!("line {line}: expected name=value, got '{tok}'"))?;
    Ok((
        name.to_ascii_lowercase(),
        Value::parse(value).map_err(|e| format!("line {line}: {e}"))?,
    ))
}

pub fn parse(text: &str) -> Result<Trace, String> {
    let mut header: BTreeMap<String, String> = BTreeMap::new();
    let mut records = Vec::new();
    let mut in_body = false;
    let mut next_cycle = 0u64;
    let mut saw_trap = false;

    for (idx, raw) in text.lines().enumerate() {
        let line = idx + 1;
        let l = raw.trim();
        if l.is_empty() || l.starts_with('#') {
            continue;
        }
        if !in_body {
            if l == "---" {
                in_body = true;
                continue;
            }
            let (k, v) = l
                .split_once(':')
                .ok_or_else(|| format!("line {line}: expected 'key: value' in header"))?;
            header.insert(k.trim().to_string(), v.trim().to_string());
            continue;
        }
        if saw_trap {
            return Err(format!("line {line}: records after a 'trap' record"));
        }
        let (lhs, rhs) = l
            .split_once("=>")
            .ok_or_else(|| format!("line {line}: record has no '=>'"))?;
        let mut lhs_toks = lhs.split_whitespace();
        let cycle: u64 = lhs_toks
            .next()
            .ok_or_else(|| format!("line {line}: missing cycle number"))?
            .parse()
            .map_err(|_| format!("line {line}: bad cycle number"))?;
        if cycle != next_cycle {
            return Err(format!(
                "line {line}: cycle {cycle} but expected {next_cycle} (records must be consecutive from 0)"
            ));
        }
        next_cycle += 1;
        let mut inputs = Vec::new();
        for tok in lhs_toks {
            let (n, v) = split_assign(tok, line)?;
            if v == Value::Any {
                return Err(format!("line {line}: '?' is not allowed as an input value"));
            }
            if inputs.iter().any(|(m, _)| *m == n) {
                return Err(format!("line {line}: input '{n}' assigned twice"));
            }
            inputs.push((n, v));
        }
        let rhs = rhs.trim();
        let expected = if rhs == "trap" {
            saw_trap = true;
            Expected::Trap
        } else {
            let mut outs = Vec::new();
            for tok in rhs.split_whitespace() {
                outs.push(split_assign(tok, line)?);
            }
            Expected::Outputs(outs)
        };
        records.push(Record {
            cycle,
            inputs,
            expected,
            line,
        });
    }

    let get = |k: &str| {
        header
            .get(k)
            .cloned()
            .ok_or_else(|| format!("header: missing '{k}'"))
    };
    let period_ms: u64 = get("period_ms")?
        .parse()
        .map_err(|_| "header: period_ms must be a positive integer".to_string())?;
    if period_ms == 0 {
        return Err("header: period_ms must be positive".into());
    }
    let program = get("program")?;
    let inputs: Vec<String> = get("inputs")?
        .split_whitespace()
        .map(|s| s.to_ascii_lowercase())
        .collect();
    let outputs: Vec<String> = get("outputs")?
        .split_whitespace()
        .map(|s| s.to_ascii_lowercase())
        .collect();
    let status = match header.get("status").map(String::as_str) {
        None | Some("conformant") => Status::Conformant,
        Some("implementation-defined") => Status::ImplementationDefined,
        Some(other) => return Err(format!("header: unknown status '{other}'")),
    };

    for r in &records {
        for (n, _) in &r.inputs {
            if !inputs.contains(n) {
                return Err(format!("line {}: '{n}' is not a declared input", r.line));
            }
        }
        if let Expected::Outputs(outs) = &r.expected {
            for (n, _) in outs {
                if !outputs.contains(n) {
                    return Err(format!("line {}: '{n}' is not a declared output", r.line));
                }
            }
            for o in &outputs {
                if outs.iter().filter(|(n, _)| n == o).count() != 1 {
                    return Err(format!(
                        "line {}: output '{o}' must appear exactly once",
                        r.line
                    ));
                }
            }
        }
    }

    Ok(Trace {
        period_ms,
        program,
        inputs,
        outputs,
        status,
        reference: header.get("reference").cloned(),
        records,
    })
}
