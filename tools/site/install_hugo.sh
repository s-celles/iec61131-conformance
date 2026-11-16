#!/usr/bin/env bash
# Install the same checksum-pinned Hugo binary used by the Nix development shell.
set -euo pipefail
cd "$(dirname "$0")/../.."
hugo_version=$(cat site/hugo-version)
case "$(uname -s)-$(uname -m)" in
  Linux-x86_64) hugo_platform=linux-amd64; hugo_sha=416bcfbdf5f68469ec9644dbe507da50fc21b94b69a125b059d64ed2cb4d8c27 ;;
  Linux-aarch64|Linux-arm64) hugo_platform=linux-arm64; hugo_sha=dc070bfcc2803f068f21c6cb996a6782c8f9a2477be24bab574d51b6b280d241 ;;
  Darwin-x86_64|Darwin-arm64) hugo_platform=darwin-universal; hugo_sha=23e59fcd6951dadc0ee7552c918970aa0c9b00659566f0fa591837e204e87d39 ;;
  *) echo "Unsupported Hugo platform: $(uname -s)-$(uname -m)" >&2; exit 1 ;;
esac
hugo_destination=${1:?usage: install_hugo.sh DIR}
mkdir -p "$hugo_destination"
hugo_tmp=$(mktemp -d)
trap 'rm -rf "$hugo_tmp"' EXIT
curl --fail --silent --show-error --location --retry 3 \
  "https://github.com/gohugoio/hugo/releases/download/v${hugo_version}/hugo_extended_${hugo_version}_${hugo_platform}.tar.gz" \
  --output "$hugo_tmp/hugo.tar.gz"
if command -v sha256sum >/dev/null; then
  printf '%s  %s\n' "$hugo_sha" "$hugo_tmp/hugo.tar.gz" | sha256sum --check
else
  printf '%s  %s\n' "$hugo_sha" "$hugo_tmp/hugo.tar.gz" | shasum -a 256 --check
fi
tar -xzf "$hugo_tmp/hugo.tar.gz" -C "$hugo_destination" hugo
"$hugo_destination/hugo" version
