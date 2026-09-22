#!/usr/bin/env bash

LIB_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_QUALITY_DIR="$(cd "${LIB_SCRIPT_DIR}/.." && pwd)"

lib_find_repo_root() {
	local dir="$1"
	while [[ "${dir}" != "/" ]]; do
		if [[ -f "${dir}/pyproject.toml" ]]; then
			echo "${dir}"
			return 0
		fi
		dir="$(dirname "${dir}")"
	done
	return 1
}

if ! LIB_REPO_ROOT="$(lib_find_repo_root "${LIB_QUALITY_DIR}")"; then
	echo "Could not find project root above ${LIB_QUALITY_DIR}" >&2
	exit 1
fi

lib_require_venv() {
	if [[ ! -d "${LIB_REPO_ROOT}/.venv" ]]; then
		echo "Missing .venv. Run: uv run task sync-dev" >&2
		exit 1
	fi
}

lib_uv_run() {
	(
		cd "${LIB_REPO_ROOT}" || exit 1
		uv run "$@"
	)
}
