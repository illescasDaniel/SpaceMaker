#!/usr/bin/env bash
# Smoke-test a built SpaceMaker AppImage (isolated HOME, no host venv).
#
# Usage: ./packaging/linux-appimage/smoke-appimage.sh [path-to-AppImage]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="${OUT_DIR:-$ROOT/dist}"

if [[ $# -ge 1 ]]; then
	APPIMAGE="$1"
else
	APPIMAGE="$(find "$OUT_DIR" -maxdepth 1 -name 'SpaceMaker-*-*.AppImage' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n 1 | cut -d' ' -f2-)"
	if [[ -z "${APPIMAGE:-}" ]]; then
		echo "error: no AppImage found under $OUT_DIR; build first or pass a path" >&2
		exit 1
	fi
fi

if [[ ! -f "$APPIMAGE" ]]; then
	echo "error: AppImage not found: $APPIMAGE" >&2
	exit 1
fi
chmod +x "$APPIMAGE"

SMOKE_HOME="$(mktemp -d "${TMPDIR:-/tmp}/spacemaker-appimage-smoke.XXXXXX")"
cleanup() {
	rm -rf "$SMOKE_HOME"
}
trap cleanup EXIT

export HOME="$SMOKE_HOME"
export PATH="/usr/bin:/bin"
unset VIRTUAL_ENV UV_PYTHON UV_PYTHON_PREFERENCE PYTHONPATH PYTHONHOME || true
mkdir -p "$HOME"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
export APPIMAGE_EXTRACT_AND_RUN=1

echo "Smoke testing $APPIMAGE (HOME=$HOME)…"
if ! "$APPIMAGE" --help | grep -q "server-only"; then
	echo "error: --help missing expected usage" >&2
	exit 1
fi

port="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
"$APPIMAGE" --server-only --port "${port}" &
pid=$!
trap 'kill "${pid}" 2>/dev/null || true; cleanup' EXIT

ready=false
for _ in $(seq 1 60); do
	if curl -sf "http://127.0.0.1:${port}/" -o /dev/null; then
		ready=true
		break
	fi
	if ! kill -0 "${pid}" 2>/dev/null; then
		echo "error: AppImage server exited early" >&2
		wait "${pid}" || true
		exit 1
	fi
	sleep 0.5
done

if [[ "${ready}" != true ]]; then
	echo "error: HTTP smoke timed out" >&2
	exit 1
fi

kill "${pid}" 2>/dev/null || true
wait "${pid}" 2>/dev/null || true
echo "smoke-appimage: OK"
