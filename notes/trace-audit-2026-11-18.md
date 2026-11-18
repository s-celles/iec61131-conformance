# Trace audit against the text of edition 2, 2026-11-18

The expected traces and their citations were written by an AI assistant
from its knowledge of IEC 61131-3; the author has no copy of the standard.
On 2026-11-18 the text of IEC 61131-3:2003 (second edition) was available
for a check. This note records what it confirms and corrects. Edition 3
(2013) citations are still unchecked, and only the points below were
compared with the text; the other derivations are not audited.

## The five conformant traces most runtimes fail

These are the traces most likely to be wrong rather than the runtimes,
since at least half of the runtimes that run them fail them.

| test | runtimes failing | ed.2 text | verdict |
|---|---|---|---|
| `edge/f_trig` | IronPLC, OpenPLC fork, RuSTy, STruC++ | 2.5.2.3.2, table 35: F_TRIG's body is `Q := NOT CLK AND NOT M; M := NOT CLK;`, and the NOTE says an F_TRIG whose CLK is FALSE has Q at 1 after its first execution following a cold restart | trace confirmed |
| `ops/limit_inverted` | matiec, OpenPLC fork, RuSTy, STruC++ | 2.5.1.5.4, table 27 feature 3: `OUT := MIN(MAX(IN,MN),MX)`, with no condition on MN and MX in the table | trace confirmed |
| `data/defaults` | rk, RuSTy, STruC++ | 2.3.3.2: the default initial value of a subrange type is its first (lower) limit unless an initial value is given | trace confirmed (its ed.2 clause was wrong, see below) |
| `config/priority_order` | IronPLC, OpenPLC fork, STruC++ | 2.7.2, rule 3: PRIORITY 0 is the highest; in non-preemptive scheduling the waiting unit with the highest priority runs first (table 50) | trace confirmed |
| `pou/fb_en_eno` | IronPLC, rk, RuSTy | 2.5.2.1a: for function blocks an EN input or ENO output "can also be provided by the manufacturer or user"; the rules then match the trace | **not supported as stated**: in ed.2 EN/ENO on a function block is optional, while the trace and the reports (ironplc#2549, PLC-lang/rusty#2036, rk item 6) treat it as implicit on every function block. Edition 3 not checked. To be decided: keep `conformant` with a note that the feature is optional, or move it out of the conformant set. |

## Edition 2 citations corrected

The comments of these traces cited the wrong ed.2 clause or table.
Only the numbers changed; no expected value and no line count changed.

| test | was | is | ed.2 title |
|---|---|---|---|
| `control-flow/case_expr` | 2.6.4.2 (an SFC clause) | 3.3.2.3 | Selection statements |
| `control-flow/nested_exit` | 2.6.5.1 (an SFC clause) | 3.3.2.4 | Iteration statements |
| `control-flow/return` | 3.3.2.3 | 3.3.2.2 | Function and function block control statements |
| `undefined/for_var_after_loop` | 2.6.5.2 | 3.3.2.4 | Iteration statements |
| `data/array_2d`, `data/array_of_struct` | 2.4.3.1 | 2.4.3.2 | Initial value assignment |
| `data/array_init`, `data/enum`, `data/struct_init`, `data/defaults` | 2.3.3.1 | 2.3.3.2 | Initialization (of derived types) |
| `ops/bit_expr_operands`, `ops/bit_literals` | table 24 for NOT/AND/OR/XOR | table 26 | Standard bitwise Boolean functions |
| `ops/literals`, `ops/bit_literals` | table 2 | table 4 | Numeric literals |
| `ops/minmax_ext_expr`, `strings/min_max_limit` | 2.5.1.5.3 | 2.5.1.5.4 | Selection and comparison functions |
| `ops/real_compare` | table 23 | table 28 | Standard comparison functions |
| `ops/real_functions` | table 24 | table 23 | Standard functions of one numeric variable |
| `ops/std_functions` | tables 24 and 26 | tables 23 and 27 | one numeric variable; selection |
| `strings/literals_escapes` | table 4 | table 5 | Character string literal features |
| `pou/fb_var_temp` | table 16b | table 16 a) | Variable declaration keywords |
| `pou/fb_en_eno` | 2.5.1.2, figure 10 | 2.5.2.1a | Use of EN and ENO in function blocks |
| `ops/time_mul` | table 24 | table 30 (features 10a, 10b) | Functions of time data types |

The other ed.2 references in the traces matched the clause or table they
name. `formal/gen_traces.py` regenerates `Traces.lean` unchanged, because
the comments are not part of the traces.
