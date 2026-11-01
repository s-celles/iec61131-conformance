# Conventions for contributors and coding agents

## Commits

- Use [Conventional Commits](https://www.conventionalcommits.org/):
  `type(scope): summary`, with types `feat`, `fix`, `docs`, `test`, `ci`,
  `refactor`, `chore`. Scopes in use: `conformance`, `harness`, `formal`,
  `ci`, `notes`.
- AI-assisted commits end with the trailer `Assisted-by: AI` — no model or
  tool name, and no `Co-Authored-By` line for the assistant. The same line
  closes pull request descriptions and upstream issues ("Assisted by AI.");
  no "Generated with ..." tool banner anywhere.
- Do not commit or push unless asked.

## Repository rules

- A `.trace` under `conformance/` with `status: conformant` is derived from
  the standard by hand; the derivation lives in the comment at the top of the
  file. Never change such a trace to match a runtime.
- After editing any `.trace`, run `python3 -I formal/gen_traces.py` and
  commit the regenerated `formal/Conformance/Traces.lean`; CI checks it is in
  sync and that `lake build` still proves the trace theorems.
- `notes/evidence/<runtime>-run.txt` records what each runtime produced at
  the commit named in `notes/evidence/COMMANDS.md` and pinned in
  `.github/workflows/ci.yml`. CI diffs the live output against it. A change
  that alters a runtime's result must update the evidence file in the same
  commit; a runtime bump must update the SHA and the evidence together.
- After editing any evidence file, run `python3 -I harness/summarize.py`: it
  regenerates the results table and totals of `notes/comparison.md` (the
  `note` column is hand-written and kept); CI checks they are in sync.
- Run Python harness scripts with `python3 -I`.

## Layout

See `README.md` for the directory layout and how to run each harness.
