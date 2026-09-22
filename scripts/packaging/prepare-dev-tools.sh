#!/usr/bin/env bash
# Populate repo-root tools/ for local development (see tools/README.md).

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
tools_dir="${repo_root}/tools"
from_path=false

for arg in "$@"; do
	case "${arg}" in
	--from-path) from_path=true ;;
	-h | --help)
		echo "Usage: prepare-dev-tools.sh [--from-path]"
		echo "  --from-path  symlink missing tools from PATH (dev convenience only)"
		exit 0
		;;
	*)
		echo "Unknown option: ${arg}" >&2
		exit 2
		;;
	esac
done

mkdir -p "${tools_dir}"

tool_names=(adb ffmpeg ffprobe magick exiftool mtp-detect mtp-getfile)
missing=()

for name in "${tool_names[@]}"; do
	target="${tools_dir}/${name}"
	if [[ -e "${target}" ]]; then
		continue
	fi
	if [[ "${from_path}" != true ]]; then
		missing+=("${name}")
		continue
	fi
	src="$(command -v "${name}" 2>/dev/null || true)"
	if [[ -z "${src}" ]]; then
		missing+=("${name}")
		continue
	fi
	ln -sf "${src}" "${target}"
	echo "linked ${name} -> ${src}"
done

if ((${#missing[@]} > 0)); then
	echo "Missing tools in ${tools_dir}: ${missing[*]}" >&2
	if [[ "${from_path}" != true ]]; then
		echo "Run with --from-path to symlink from PATH, or copy release binaries here." >&2
	fi
	exit 1
fi

echo "All bundled tools present under ${tools_dir}"
