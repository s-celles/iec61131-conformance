# Contributing

Contributions are welcome: a test, a harness for another runtime, a
correction to a trace, a fix to the tools. `docs/guide.md` explains how to
write a test, add a runtime and run the checks.

## Declarations

Every contributor declares, in `docs/disclosures.tsv`, their relations to
the implementations the suite evaluates and how an AI assistant was used.
A change that adds or modifies a test, a trace, a harness, a check or the
list of runtimes is not complete without the rows of the person it is made
by:

- one row per evaluated runtime you have a relation with (author,
  maintainer, contributor, employee, funded by, issue reporter), kind
  `examined system`; a runtime without a row shows as "none";
- one row of kind `AI assistance`: what an AI assistant did and how you
  reviewed its output, or that you used none. Do not name the tool;
- your relation to the suite itself (kind `benchmark`), and anything else
  a reader should know (kind `other`).

An AI agent working on the repository adds or updates these rows for the
person it works for, and describes itself in the AI assistance row as "an
AI assistant". Lines starting with `#` are comments. The site's Conflict of interest
page (menu entry Disclosure) is generated from the file; do not write the declarations anywhere else.

## Rules

- A trace with `status: conformant` follows from the standard and is never
  changed to match a runtime.
- Commits follow Conventional Commits; AI-assisted commits end with
  `Assisted-by: AI`.
- A change that alters a runtime's result updates its evidence file in the
  same pull request (`notes/evidence/`).
