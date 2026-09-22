#!/usr/bin/env bash

set -euo pipefail

quality_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=internal/lib.sh
source "${quality_dir}/internal/lib.sh"

FIX=false
for arg in "$@"; do
	case "${arg}" in
	--fix) FIX=true ;;
	esac
done

if [[ ! -f "${LIB_REPO_ROOT}/package.json" ]]; then
	echo "skip web: no package.json" >&2
	exit 0
fi

if ! command -v npm >/dev/null 2>&1; then
	echo "skip web: npm not installed (run npm ci when Node is available)" >&2
	exit 0
fi

if [[ ! -d "${LIB_REPO_ROOT}/node_modules/@biomejs/biome" ]]; then
	echo "Missing node_modules. Run: npm ci" >&2
	exit 1
fi

(
	cd "${LIB_REPO_ROOT}" || exit 1
	if [[ "${FIX}" == true ]]; then
		npm run fix
	else
		npm run check
	fi
)
