#!/usr/bin/env bash
# Build the project site into OUT/public, entirely outside the repository:
#   tools/site/build.sh OUT [HUGO]
# OUT/content and OUT/static come from tools/site/sitegen.py; HUGO defaults
# to hugo on PATH (tools/site/install_hugo.sh DIR installs the pinned one).
set -euo pipefail
out=$(mkdir -p "$1" && cd "$1" && pwd)
hugo=${2:-hugo}
root=$(cd "$(dirname "$0")/../.." && pwd)
case "$out/" in "$root"/*) echo "OUT must be outside the repository" >&2; exit 1 ;; esac
python3 -I "$root/tools/site/sitegen.py" --root "$root" --out "$out"
rm -rf "$out/public"
HUGO_RESOURCEDIR="$out/resources" "$hugo" --source "$root/site" --contentDir "$out/content" \
  --destination "$out/public" --minify ${HUGO_BASEURL:+--baseURL "$HUGO_BASEURL"}
cp -r "$out/static/." "$out/public/"
mkdir -p "$out/public/brand"
cp "$root"/assets/brand/*.svg "$out/public/brand/"
echo "site: $out/public"
