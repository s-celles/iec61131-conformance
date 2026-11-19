#!/usr/bin/env python3
"""Write notes/upstream-status.tsv: the state of every upstream issue and
pull request the notes cite, read from GitHub with `gh api`.

    python3 -I tools/site/upstream_status.py

The site shows these states; they are a dated snapshot, refreshed by running
this script (it needs `gh` and network access), not read at build time, so
that a build is reproducible offline.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "site"))
import sitegen  # noqa: E402

COLUMNS = ("repo", "number", "kind", "state", "created", "closed", "title")


def fetch(repo, number):
    out = subprocess.run(["gh", "api", f"repos/{repo}/issues/{number}"], capture_output=True, text=True)
    if out.returncode != 0:
        return {"repo": repo, "number": number, "kind": "?", "state": "unknown", "created": "", "closed": "", "title": ""}
    d = json.loads(out.stdout)
    kind, state = ("pr", d["state"]) if "pull_request" in d else ("issue", d["state"])
    if kind == "pr" and (d.get("pull_request") or {}).get("merged_at"):
        state = "merged"
    elif kind == "issue" and d.get("state_reason") == "not_planned":
        state = "closed (not planned)"
    return {"repo": repo, "number": number, "kind": kind, "state": state, "created": (d.get("created_at") or "")[:10],
            "closed": (d.get("closed_at") or "")[:10], "title": " ".join(d.get("title", "").split()).replace("\t", " ")}


def main():
    refs = sitegen.Site(ROOT).refs
    rows = [fetch(r, n) for r, n in refs]
    lines = ["\t".join(COLUMNS)] + ["\t".join(str(row[c]) for c in COLUMNS) for row in rows]
    (ROOT / "notes" / "upstream-status.tsv").write_text("\n".join(lines) + "\n")
    print(f"{len(rows)} upstream references written to notes/upstream-status.tsv")


if __name__ == "__main__":
    main()
