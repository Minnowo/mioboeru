#!/bin/bash
# Download the single-page Anki add-on docs for offline reference.

set -euo pipefail

readonly root_dir=$(git rev-parse --show-toplevel)
readonly url=https://addon-docs.ankiweb.net/print.html
readonly out=$root_dir/docs/anki-addon-docs.html

mkdir -p -- "$(dirname -- "$out")"
curl -sSfL "$url" -o "$out"
echo "Saved $url -> $out"
