#!/usr/bin/env python3
"""Write notes/upstream-status.tsv: the state of every upstream issue and
pull request the notes cite, read from GitHub with `gh api`.

    python3 -I tools/site/upstream_status.py

The site shows these states; they are a dated snapshot, refreshed by running
this script (it needs `gh` and network access), not read at build time, so
that a build is reproducible offline. The columns are the shared snapshot
schema of site-kit (SPEC.md §6); cited_by lists the findings that cite the
reference. A reference that cannot be fetched keeps its previous row.
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "site"))
import sitegen  # noqa: E402

COLUMNS = ("repo", "number", "kind", "state", "created", "closed", "merged", "fixes", "cited_by", "title")
FIXES = re.compile(r"(?i)\b(?:fix(?:e[sd])?|close[sd]?|resolve[sd]?)\s*:?\s+((?:[\w.-]+/[\w.-]+)?#\d+)")


def clean(text):
    return " ".join((text or "").split())


def row(repo, d, cited_by):
    """A snapshot row from the issues endpoint's JSON for repo#number."""
    pr = d.get("pull_request")
    kind, state = ("pr" if pr is not None else "issue"), d.get("state", "")
    merged = ((pr or {}).get("merged_at") or "")[:10]
    if merged:
        state = "merged"
    elif kind == "issue" and state == "closed" and d.get("state_reason") == "not_planned":
        state = "not planned"
    fixes = []
    for ref in FIXES.findall(d.get("body") or "") if pr is not None else []:
        ref = f"{repo}{ref}" if ref.startswith("#") else ref
        if ref not in fixes:
            fixes.append(ref)
    return {"repo": repo, "number": str(d.get("number", "")), "kind": kind, "state": state,
            "created": (d.get("created_at") or "")[:10], "closed": (d.get("closed_at") or "")[:10], "merged": merged,
            "fixes": " ".join(fixes), "cited_by": " ".join(sorted(cited_by)), "title": clean(d.get("title"))}


def main():
    site = sitegen.Site(ROOT)
    cited = {}
    for f in site.findings:
        for ref in f["refs"]:
            cited.setdefault(tuple(ref), set()).add(f["id"])
    old = sitegen.upstream_snapshot(ROOT)
    rows = []
    for r, n in site.refs:
        out = subprocess.run(["gh", "api", f"repos/{r}/issues/{n}"], capture_output=True, text=True)
        if out.returncode == 0:
            rows.append(row(r, json.loads(out.stdout), cited.get((r, n), set())))
        else:
            prev = dict(old.get((r, n)) or {"repo": r, "number": str(n), "state": "unknown"})
            prev["cited_by"] = " ".join(sorted(cited.get((r, n), set())))
            rows.append(prev)
            print(f"kept the previous row of {r}#{n}: {out.stderr.strip()}", file=sys.stderr)
    lines = ["\t".join(COLUMNS)] + ["\t".join(clean(str(x.get(c, ""))) for c in COLUMNS) for x in rows]
    (ROOT / "notes" / "upstream-status.tsv").write_text("\n".join(lines) + "\n")
    print(f"{len(rows)} upstream references written to notes/upstream-status.tsv")


if __name__ == "__main__":
    main()
