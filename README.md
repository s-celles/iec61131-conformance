<p align="center"><img src="assets/brand/scanard-banner.svg" alt="SCANard: expected vs. observed, one scan at a time"></p>

# IEC 61131-3 conformance traces

[![CI](https://github.com/s-celles/iec61131-conformance/actions/workflows/ci.yml/badge.svg)](https://github.com/s-celles/iec61131-conformance/actions/workflows/ci.yml)
[![Site](https://github.com/s-celles/iec61131-conformance/actions/workflows/site.yml/badge.svg)](https://s-celles.github.io/iec61131-conformance/)

An open, runtime-agnostic conformance suite for IEC 61131-3 Structured Text:
plain `.st` programs paired with expected input/output traces, one record
per scan cycle. The suite runs against IronPLC, matiec, OpenPLC's matiec fork,
STruC++, 4diac, rk, RuSTy and truST, and a Lean 4 model of the function blocks
proves their traces. Public domain (CC0 1.0).

**Results, tests and findings: https://s-celles.github.io/iec61131-conformance/**

> [!IMPORTANT]
> An individual, non-commercial project. It is not produced, endorsed or
> certified by IEC, PLCopen, any accredited or standards body, or the
> projects whose runtimes it runs. Its aim is to help improve existing
> open-source IEC 61131-3 implementations by reporting reproducible
> differences.
>
> The expected traces, their derivations and the clause and table numbers
> they cite were written by an AI assistant from its knowledge of the
> standard. The author does not consult the text of IEC 61131-3 for this
> project, so they are not checked against it and may contain errors. A
> failed trace is a claim to
> check, not a verdict; corrections from anyone with the text are welcome.
> On 2026-11-18 the edition 2 citations and the five traces most runtimes
> fail were checked against the text of IEC 61131-3:2003
> ([notes/trace-audit-2026-11-18.md](notes/trace-audit-2026-11-18.md)).
> The results cover the runtime commits pinned in CI only.
>
> Conflicts of interest and AI assistance of each contributor are declared
> at https://s-celles.github.io/iec61131-conformance/disclosure/.

```
conformance/   the tests: <name>.st + <name>.trace     SPEC.md       trace format
harness/       one driver per runtime                  notes/        results, findings, evidence
formal/        Lean 4 model and trace theorems         tools/        fuzzer, property monitors, site
```

Running the runtimes, the CI, writing a test, fuzzing: [docs/guide.md](docs/guide.md).
Changes: [CHANGELOG.md](CHANGELOG.md). Citation: [CITATION.cff](CITATION.cff).
Written with AI assistance (commits carry `Assisted-by: AI`).
