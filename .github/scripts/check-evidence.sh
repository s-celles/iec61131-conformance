#!/usr/bin/env bash
# Runs a harness command, captures stdout plus its exit status the way
# notes/evidence/*-run.txt were recorded ("exit N" as last line), and diffs
# the result against the committed evidence file.
#
# The runtimes are known to fail some conformant tests (notes/findings.md),
# so the harness exit status alone cannot gate CI. What this checks instead
# is that, at the pinned runtime commit, the suite still produces exactly the
# recorded results: any change to a .st/.trace/harness that alters the
# outcome shows up as a diff and must come with an updated evidence file.
#
# Before diffing, both sides are normalised: ANSI colour codes are stripped,
# per-run temporary directories (/tmp/rusty-<test>-XXXX/) are masked, and
# the suite's absolute root (which ironplcc quotes in diagnostics) is
# replaced by <root>, and the runner's temp dir (where CI builds the
# runtimes) by <tmp>, and the Rust toolchain source path ironplcc's P9999
# "Learn more" URL carries by <file>, since compiler diagnostics quote them;
# the 4diac harness's temporary dirs, FORTE path and the Eclipse log
# timestamps (!ENTRY lines) are masked too.
#
# Usage: check-evidence.sh EVIDENCE_FILE -- COMMAND...
set -uo pipefail
evidence=$1; shift
[ "$1" = "--" ] && shift
out=$(mktemp)
"$@" > "$out"
echo "exit $?" >> "$out"
name=$(basename "$evidence")
cp "$out" "${RUNNER_TEMP:-/tmp}/$name"
summary=$(grep -E '^[0-9]+ tests:' "$out" || echo "no summary line")
root=$(pwd -P)
normalise() { sed -E -e $'s/\x1b\\[[0-9;]*m//g' -e 's#/tmp/[A-Za-z0-9_.-]+/#<tmpdir>/#g' -e "s#$root/#<root>/#g" -e "s#${RUNNER_TEMP:-/nonexistent}/#<tmp>/#g" -e 's#<tmp>/strucpp/#<strucpp>/#g'  -e 's/&file=[^&]*&line=[0-9]+/\&file=<file>\&line=<n>/g' -e 's#/private/var/folders/[^ ]*/T/4diac-[A-Za-z0-9_]+/#<tmpdir>/#g' -e 's#/var/folders/[^ ]*/T/4diac-[A-Za-z0-9_]+/#<tmpdir>/#g' -e 's#<tmp>/4diac-forte/#<forte>/#g' -e 's#<tmpdir>/4diac-[A-Za-z0-9_]+/#<tmpdir>/#g' -e 's/^(\s*!(ENTRY|SESSION) .*) [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]+/\1 <timestamp>/' "$1"; }
if diff -u --label "$evidence" --label "harness output" <(normalise "$evidence") <(normalise "$out"); then
  echo "### $name: matches evidence — $summary" >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
else
  echo "### $name: DIFFERS from evidence — $summary" >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
  echo "::error file=$evidence::harness output differs from $evidence (see diff above; regenerate it if the change is intended)"
  exit 1
fi
