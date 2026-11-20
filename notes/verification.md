# Verification by a person against the standard

The expected traces of this suite were derived by an AI assistant without
access to the text of IEC 61131-3. This file lets anyone who has a
licensed copy check them without the text being quoted here: each sheet
states one claim in the assistant's own words and asks a closed question;
a reader answers from the standard, in an issue or a pull request, with a
verdict and a clause or table number, nothing more (no quotation, no
paraphrase of the text). The trace then keeps `status: conformant` with
"checked against ed.N" in its comment, is corrected, or becomes
`implementation-defined`. No sheet has been answered yet.

Answer format, on the `Answer` line of each sheet:

- `yes, <edition> <clause/table>`: the claim holds;
- `no, <edition> <clause/table>: <the correct value or rule, in a few words>`;
- `not in <edition>`: the standard does not settle it (the trace becomes
  implementation-defined or is dropped);
- `skip`: not checked this time.

Edition consulted (ed.3 2013, or ed.4 if available): `____`

## New tests (batch 1)

### V-01 `pou/fb_edge_inputs`: R_EDGE and F_EDGE inputs

- Claim: a function block input declared `VAR_INPUT r : BOOL R_EDGE;`
  reads TRUE inside the body at an invocation where the actual input is
  TRUE and was FALSE at the previous invocation (the first invocation
  counting as "previous FALSE"); `F_EDGE` reads TRUE where it is FALSE
  and was TRUE. It behaves like an R_TRIG / F_TRIG applied to the input.
- Where to look: declaration of edge-detecting inputs (ed.2 had it in
  2.5.2.2 with the FB declaration features).
- Question: are `R_EDGE` and `F_EDGE` input qualifiers in the edition
  you consulted, with this meaning?
- Answer:

### V-02 `ops/compare_extensible`: GT, GE, EQ, LE, LT with three inputs

- Claim: the comparison functions except NE accept more than two inputs,
  and `GT(a, b, c)` means `(a > b) AND (b > c)`, each input compared with
  the next one (not each with the first).
- Where to look: the table of the comparison functions (ed.3 table 28 by
  our citations).
- Question: is the result the conjunction of the comparisons of
  consecutive inputs?
- Answer:

### V-03 `ops/mod_negative`: integer division and MOD on negatives

- Claim: dividing two integers truncates toward zero (`-7 / 2 = -3`), and
  `a MOD b` for `b <> 0` equals `a - (a / b) * b`, so `-7 MOD 2 = -1` and
  `7 MOD -2 = 1`.
- Where to look: the arithmetic functions table (DIV, MOD) and its notes
  (ed.3 table 29 by our citations).
- Questions: (a) truncation toward zero, yes or no? (b) MOD defined by
  that formula, yes or no? (c) what does the standard give for `a MOD 0`
  (we do not test it yet)?
- Answer:

### V-04 `data/long_types`: LINT, ULINT, LWORD

- Claim: LINT is 64-bit signed, ULINT 64-bit unsigned, LWORD a 64-bit bit
  string; `LWORD_TO_DWORD` keeps the 32 least significant bits; SHR and
  ROL work on all 64 bits.
- Where to look: elementary data types table; type conversion of bit
  strings; bit shift functions.
- Questions: (a) the ranges, yes or no? (b) a bit-string conversion to a
  shorter type keeps the least significant bits, yes or no?
- Answer:

### V-05 `ops/bcd_conversions`: BCD conversions

- Claim: the edition has the typed functions `WORD_BCD_TO_UINT` and
  `UINT_TO_BCD_WORD`, with one decimal digit per nibble, so 1234 and
  16#1234 correspond.
- Where to look: the type conversion table, BCD rows.
- Questions: (a) are these the exact function names (or which names)?
  (b) the digit layout, yes or no?
- Answer:

### V-06 `ops/move`: MOVE

- Claim: `MOVE(IN)` returns its input unchanged, for any type; its input
  is named `IN`.
- Where to look: the MOVE row (with the conversion or selection
  functions).
- Question: yes or no, and is the input named `IN`?
- Answer:

### V-07 `data/enum_qualified`: type-qualified enumerated values

- Claim: two enumerated types may share a value name (`red` in `Color`
  and in `Light`); `Color#red` names that type's value and is usable in
  assignments, comparisons and CASE labels.
- Where to look: enumerated data types (ed.3 6.4.4.1 by our citations).
- Question: is sharing a value name between types allowed with the
  `Type#value` form?
- Answer:

### V-08 `data/var_constant`: VAR CONSTANT

- Claim: a variable declared in `VAR CONSTANT` keeps its declared value
  and may be read in an expression, a comparison and as a FOR bound.
- Where to look: variable declaration qualifiers (CONSTANT).
- Question: yes or no (and the clause)?
- Answer:

### V-09 (no test yet): a program without a task

- Question before writing a test: in a CONFIGURATION, how often does a
  program with no task association run, and at which priority? (We
  remember "lowest priority, run continuously", which needs a precise
  meaning for one scan per record.)
- Answer:

## Existing traces that several runtimes fail

The traces below are failed by three or four of the eight runtimes, so an
error in the trace would mislead an upstream report. Each sheet repeats
what the trace claims; its comment gives the full derivation.

### V-10 `edge/f_trig`: F_TRIG on its first evaluation

- Claim: an F_TRIG whose CLK is FALSE at its first evaluation after a
  cold restart gives Q = TRUE there (M starts FALSE, Q := NOT CLK AND
  NOT M), and Q = FALSE afterwards while CLK stays FALSE.
- Where to look: the edge detection table and its note.
- Answer:

### V-11 `ops/limit_inverted`: LIMIT with MN > MX

- Claim: LIMIT is defined as `MIN(MAX(IN, MN), MX)`, with no
  requirement that MN <= MX, so LIMIT(MN := 5, IN := 3, MX := 1) = 1.
- Where to look: the selection functions table, LIMIT row.
- Answer:

### V-12 `ops/time_mul`: TIME * INT

- Claim: multiplying a TIME by an integer scales the duration exactly:
  T#999ms * 3 = T#2997ms, T#71487ms * 44 = T#3145428ms.
- Where to look: the arithmetic on time types table (MUL on TIME and
  ANY_NUM / ANY_INT).
- Answer:

### V-13 `strings/declared_length`: STRING[n]

- Claim: `STRING[n]` holds up to n characters; a value of at most n
  characters is stored whole; a named type may be a `STRING[n]`.
- Where to look: elementary data types (STRING), derived types.
- Answer:

### V-14 `strings/functions`: LEFT, RIGHT, MID, INSERT, DELETE, REPLACE, FIND

- Claim: positions count from 1; `MID(IN, L, P)` is L characters from
  the P-th; `INSERT(IN1, IN2, P)` inserts IN2 after the P-th character;
  `DELETE(IN, L, P)` deletes L characters from the P-th;
  `REPLACE(IN1, IN2, L, P)` replaces L characters from the P-th; `FIND`
  returns 0 when absent.
- Where to look: the character string functions table.
- Answer:

### V-15 `strings/find_int`: the type of FIND's result

- Claim: FIND (and LEN) return an INT, a signed type, so `FIND(...) - 5`
  is negative when FIND gives 2.
- Where to look: the character string functions table (result types).
- Answer:

### V-16 `pou/fb_method`: methods

- Claim: a method declared without an access specifier is PROTECTED, so
  the test declares its methods PUBLIC to call them from `main`; a
  method reads and writes the instance's variables; its return value may
  be used or discarded.
- Where to look: methods of function blocks, access specifiers.
- Answer:

### V-17 `pou/fb_en_eno`: EN and ENO on a function block

- Claim: with EN FALSE at the invocation the body is not executed and ENO
  is FALSE; with EN TRUE the body runs and ENO is TRUE; ENO is read with
  `ENO =>` in the call.
- Where to look: EN and ENO (ed.3 6.6.1.5 by our citations), and whether
  EN/ENO on a function block is optional in that edition.
- Answer:

### V-18 `ops/std_functions_ext`: extensible ADD, MUL, MAX, MIN

- Claim: ADD, MUL, MAX and MIN accept more than two inputs; LIMIT's
  inputs are named MN, IN, MX and SEL's G, IN0, IN1.
- Where to look: extensible functions; the arithmetic and selection
  tables.
- Answer:

### V-19 `ops/std_formal_order`: order of formal arguments

- Claim: in a formal call the order of the assignments does not matter;
  MUX's inputs are named K, IN0, IN1, ...
- Where to look: function invocation (formal), the MUX row.
- Answer:

### V-20 `data/defaults`: default initial values

- Claim: the defaults are FALSE, 0, 0.0, T#0s and the empty string; an
  enumerated variable starts at its first value; a subrange variable at
  its lower limit; array and structure elements take their types'
  defaults.
- Where to look: the default initial values column of the data types
  table; the initial value rules for enumerations and subranges.
- Answer:

### V-21 `config/priority_order`: task priority

- Claim: PRIORITY 0 is the highest; with non-preemptive scheduling, of
  the tasks ready at the same time the one with the highest priority runs
  first, so a writer at priority 0 runs before a reader at priority 1.
- Where to look: tasks, PRIORITY, scheduling.
- Answer:
