#!/usr/bin/env bash
# Portable release build → dist/ (gitignored). Linux: pruned AppDir; other OS: PyInstaller onefile.

set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo}"

if [[ "$(uname -s)" == "Linux" ]]; then
	echo "Linux: building pruned AppDir (use build-appimage to pack)…"
	APPDIR="${repo}/dist/spacemaker-linux.AppDir"
	export APPDIR
	bash "${repo}/packaging/linux-appimage/build-appdir.sh"
	echo "OK: ${APPDIR} ($(du -sh "${APPDIR}" | cut -f1))"
	exit 0
fi

echo "Syncing dev dependencies (includes PyInstaller)…"
uv sync --group dev

echo "Syncing brand icons…"
uv run python scripts/packaging/sync_brand_icons.py

echo "Building onefile artifact in dist/…"
uv run pyinstaller packaging/spacemaker.spec --noconfirm

artifact="${repo}/dist/SpaceMaker"
if [[ "$(uname -s)" == "MINGW"* || "$(uname -s)" == "CYGWIN"* || "$(uname -s)" == "MSYS"* ]]; then
	artifact="${repo}/dist/SpaceMaker.exe"
fi
if [[ ! -f "${artifact}" ]]; then
	echo "error: expected artifact missing: ${artifact}" >&2
	exit 1
fi

echo "Smoke test: --help and --server-only HTTP…"
if ! "${artifact}" --help | grep -q "server-only"; then
	echo "error: --help did not print expected usage" >&2
	exit 1
fi

port="$(
	uv run python -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()'
)"
"${artifact}" --server-only --port "${port}" &
smoke_pid=$!
trap 'kill "${smoke_pid}" 2>/dev/null || true' EXIT

ready=false
for _ in $(seq 1 60); do
	if curl -sf "http://127.0.0.1:${port}/" -o /dev/null; then
		ready=true
		break
	fi
	if ! kill -0 "${smoke_pid}" 2>/dev/null; then
		echo "error: binary exited before HTTP was ready (port ${port})" >&2
		wait "${smoke_pid}" || true
		exit 1
	fi
	sleep 0.5
done

if [[ "${ready}" != true ]]; then
	echo "error: HTTP smoke test timed out on port ${port}" >&2
	exit 1
fi

kill "${smoke_pid}" 2>/dev/null || true
wait "${smoke_pid}" 2>/dev/null || true
trap - EXIT

echo "OK: ${artifact} ($(du -h "${artifact}" | cut -f1))"
