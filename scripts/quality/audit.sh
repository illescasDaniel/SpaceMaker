#!/usr/bin/env bash

set -euo pipefail

quality_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=internal/lib.sh
source "${quality_dir}/internal/lib.sh"

# Known-vulnerability audit of the locked dependencies (needs network). Mirrors step_audit in checks.py.
req="$(mktemp)"
trap 'rm -f "${req}"' EXIT
(cd "${LIB_REPO_ROOT}" && uv export --quiet --frozen --no-emit-project --all-groups --no-hashes -o "${req}")
uvx pip-audit -r "${req}" --no-deps --disable-pip
if [[ -f "${LIB_REPO_ROOT}/package-lock.json" ]] && command -v npm >/dev/null 2>&1; then
	(cd "${LIB_REPO_ROOT}" && npm audit --audit-level=high)
fi
