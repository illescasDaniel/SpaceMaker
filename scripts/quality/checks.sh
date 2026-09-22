#!/usr/bin/env bash

set -u

quality_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=internal/lib.sh
source "${quality_dir}/internal/lib.sh"

FIX=false
QUIET=false
SKIP_WEB=false

for arg in "$@"; do
	case "${arg}" in
	--fix) FIX=true ;;
	--quiet) QUIET=true ;;
	--skip-web) SKIP_WEB=true ;;
	esac
done

log() {
	if [[ "${QUIET}" != true ]]; then
		echo "$@"
	fi
}

fail=0

run_step() {
	local name="$1"
	shift
	log "== ${name} =="
	if "$@"; then
		log "ok: ${name}"
	else
		echo "fail: ${name}" >&2
		fail=1
	fi
}

lib_require_venv

if [[ "${FIX}" == true ]]; then
	run_step ruff "${quality_dir}/ruff.sh"
else
	run_step ruff "${quality_dir}/ruff.sh" --check
fi

run_step ty "${quality_dir}/ty.sh"
run_step pytest "${quality_dir}/pytest.sh"

if [[ "${SKIP_WEB}" != true ]]; then
	if [[ "${FIX}" == true ]]; then
		run_step web "${quality_dir}/web.sh" --fix
	else
		run_step web "${quality_dir}/web.sh"
	fi
fi

exit "${fail}"
