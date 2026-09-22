#!/usr/bin/env bash

set -euo pipefail

quality_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=internal/lib.sh
source "${quality_dir}/internal/lib.sh"

CHECK_ONLY=false
for arg in "$@"; do
	case "${arg}" in
	--check) CHECK_ONLY=true ;;
	esac
done

lib_require_venv
targets=(src tests)

if [[ "${CHECK_ONLY}" == true ]]; then
	lib_uv_run ruff check "${targets[@]}"
	lib_uv_run ruff format --check "${targets[@]}"
else
	lib_uv_run ruff check "${targets[@]}" --fix
	lib_uv_run ruff format "${targets[@]}"
fi
