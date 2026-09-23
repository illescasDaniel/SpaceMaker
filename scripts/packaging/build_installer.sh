#!/usr/bin/env bash
# Portable onefile executable → dist/ (gitignored). See packaging/README.md.

set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo}"

echo "Syncing dev dependencies (includes PyInstaller)…"
uv sync --group dev

echo "Building onefile installer artifact in dist/…"
uv run pyinstaller packaging/spacemaker.spec --noconfirm

artifact="${repo}/dist/SpaceMaker"
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
