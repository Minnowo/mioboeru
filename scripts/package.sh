#!/bin/bash
# Build ajt_mioboeru.ankiaddon (includes the ajt_common submodule).
# Requires: git, zip, zipmerge.

set -euo pipefail

readonly root_dir=$(git rev-parse --show-toplevel)
cd -- "$root_dir"

"$root_dir/mioboeru/ajt_common/package.sh" \
	--package "AJT Mioboeru" \
	--name "AJT Mioboeru" \
	--root "mioboeru" \
	"$@"
