# Trace format specification (version 1)

A conformance test is a pair of files with the same stem:

- `<name>.st`: a plain IEC 61131-3 Structured Text file containing exactly one
  `PROGRAM`, plus any `FUNCTION` / `FUNCTION_BLOCK` it needs. No
  `CONFIGURATION`: the runtime under test is expected to run the program as a
  single cyclic task at the period given by the trace.
- `<name>.trace`: the expected input/output behaviour, cycle by cycle, in the
  plain-text format below.

The format is deliberately the line-oriented transcription of the step script
IronPLC's own end-to-end tests use (`write(name, v)`, `run(t)`,
`expect(name, v)` in `codegen/tests/it/end_to_end_*.rs`) and of the
stimulus/trace model specified for the IronPLC MCP `run` tool
(REQ-TOL-mcp-041/042 in `specs/design/mcp-server.md`): inputs are applied at
the start of a cycle, persist until overwritten, and outputs are sampled at
the end of the cycle.

## File structure

```
# comment lines start with '#', anywhere in the file; blank lines are ignored
period_ms: 100
program: main
inputs: in
outputs: q et
status: conformant
---
0 in=FALSE => q=FALSE et=T#0ms
1 in=TRUE  => q=FALSE et=T#0ms
2          => q=FALSE et=T#100ms
```

A header of `key: value` lines, a separator line `---`, then one record per
cycle.

### Header keys

| key | required | meaning |
|---|---|---|
| `period_ms` | yes | cycle period in milliseconds (positive integer). Cycle `n` starts at PLC time `t = n * period_ms`. |
| `program` | yes | name of the `PROGRAM` in the `.st` file (the entry point, one instance). |
| `inputs` | yes | space-separated names of the program-scope variables the harness writes. May be empty. |
| `outputs` | yes | space-separated names of the program-scope variables the harness reads and compares. |
| `status` | no | `conformant` (default): the expected values follow from the standard. `implementation-defined`: the expected values are what one named runtime does; a mismatch is a **difference**, not a failure. |
| `reference` | no | free text: which clause / table / figure of IEC 61131-3 the expectation is derived from. |

Names are IEC identifiers and are matched case-insensitively. All named
variables must be declared in the program's `VAR`, `VAR_INPUT` or
`VAR_OUTPUT` section with one of the types `BOOL`, `INT`, `DINT`, `UINT`,
`TIME`, `BYTE`, `WORD`, `DWORD` (version 1 scope).

### Records

```
<cycle> [<input>=<value> ...] => <output>=<value> ...
```

- `<cycle>` is a decimal integer. Records must be consecutive and start at 0.
- Tokens are separated by one or more spaces or tabs. There is exactly one
  `=>` per record.
- Each `name=value` token to the left of `=>` is an **input assignment** applied
  before the cycle runs. An input not mentioned keeps the value it had in the
  previous record; before cycle 0 every input holds the initial value its
  declaration gives it (the IEC default initial value if none is declared).
  Writing the same input twice in one record is an error.
- Each `name=value` token to the right of `=>` is an **expected output** at the
  end of the cycle. Every name in `outputs` must appear exactly once, in any
  order.
- The special output value `?` means "not checked on this cycle". It exists
  for the cycles where the standard text leaves the value genuinely open (for
  example `ET` on the very cycle a `TP` pulse ends); it must be justified in a
  comment and must be rare.
- The special right-hand side `trap` (no outputs) means the runtime is expected
  to stop the cycle with a runtime error (division by zero, ...). Nothing is
  checked after a `trap` record; the record must be the last one.

### Values

| type | syntax | examples |
|---|---|---|
| `BOOL` | `TRUE` or `FALSE` | `q=TRUE` |
| `INT`, `DINT`, `UINT` | optional sign and decimal digits | `x=-32768`, `n=65535` |
| `TIME` | `T#<n>ms`, non-negative integer milliseconds only | `et=T#1500ms` |
| `BYTE`, `WORD`, `DWORD` | `16#` and exactly 2, 4 or 8 upper-case hex digits | `w=16#00FF`, `d=16#DEADBEEF` |

No other literal forms are allowed (no `T#1.5s`, no `16#` on integers, no
`INT#`), so a parser is a split on whitespace, a split on the first `=`, and
four cases. This is the rendering `ironplcvm run --dump-vars` produces, so a
dump can be compared to a record by string equality.

Arrays, structures and enumerations may be used inside the program; the
harness only reads and writes scalars of the types above, so expose what is
to be checked through scalar program variables.

## Semantics the harness must implement

1. Compile `<name>.st`. Start the program with its declared initial values.
2. For cycle `n = 0, 1, 2, ...` in record order:
   a. apply the record's input assignments (write the program variables);
   b. run exactly one scan of the program at PLC time `t = n * period_ms`
      (for a runtime with a real clock, the harness must be able to substitute
      a simulated time; a runtime that cannot is out of scope);
   c. read every output and compare with the record. Report `pass` or `fail`
      per cycle, and for `status: implementation-defined` traces report
      `same` or `differs`.
3. A trap on a cycle whose record is not `trap` is a failure of that cycle,
   and the test stops there.

## What a trace deliberately does not express

- Multi-task configurations, task priorities, event tasks.
- Located variables (`%I`, `%Q`); the harness writes program variables.
- Values of function block instance fields; expose them through program
  outputs instead (`et := timer.ET;` or `ET => et`).
- Timing inside a cycle: every input is visible for the whole cycle, every
  output is sampled once at the end.

## Grammar (ABNF-ish)

```
file     = *( comment / blank ) header *( header-line ) sep *( record / comment / blank )
header-line = key ":" SP *VCHAR LF
sep      = "---" LF
record   = cycle *( SP assign ) SP "=>" ( *( SP assign ) / SP "trap" ) LF
assign   = name "=" value
value    = "TRUE" / "FALSE" / ["-"] 1*DIGIT / "T#" 1*DIGIT "ms"
         / "16#" ( 2HEXDIG / 4HEXDIG / 8HEXDIG ) / "?"
comment  = "#" *VCHAR LF
```
