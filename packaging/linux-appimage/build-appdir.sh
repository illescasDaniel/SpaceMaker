#!/usr/bin/env bash
# Build a relocatable Linux AppDir (managed CPython + venv + pruned PyQt6 WebEngine).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APPDIR="${APPDIR:-$ROOT/build/SpaceMaker.AppDir}"
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"

cd "$ROOT"

if [[ "$(uname -s)" != "Linux" ]]; then
	echo "error: AppDir build is supported on Linux only" >&2
	exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
	echo "error: uv is required" >&2
	exit 1
fi

echo "Syncing brand icons…"
uv run python scripts/packaging/sync_brand_icons.py

echo "AppDir: $APPDIR"
rm -rf "$APPDIR/usr"
mkdir -p "$APPDIR/usr/share/spacemaker/packaging/assets"

echo "Installing managed CPython ${PYTHON_VERSION} into AppDir…"
export UV_PYTHON_PREFERENCE=only-managed
export UV_LINK_MODE=copy
uv python install "$PYTHON_VERSION" --install-dir "$APPDIR/usr/python" --no-bin
APP_PYTHON="$(find "$APPDIR/usr/python" -type f \( -name "python${PYTHON_VERSION}" -o -name python3 -o -name python \) | head -n 1)"
if [[ -z "$APP_PYTHON" || ! -x "$APP_PYTHON" ]]; then
	echo "error: managed python not found under $APPDIR/usr/python" >&2
	exit 1
fi

echo "Creating relocatable AppDir venv…"
uv venv --python "$APP_PYTHON" --relocatable --link-mode copy "$APPDIR/usr/venv"
VENV_PY="$APPDIR/usr/venv/bin/python"
VENV_BIN="$APPDIR/usr/venv/bin"
REL_PY="$(realpath --relative-to="$VENV_BIN" "$APP_PYTHON")"
for name in python "python${PYTHON_VERSION}" python3; do
	link="$VENV_BIN/$name"
	if [[ -e "$link" || -L "$link" ]]; then
		ln -sfn "$REL_PY" "$link"
	fi
done
if [[ -f "$APPDIR/usr/venv/pyvenv.cfg" ]]; then
	REL_HOME="$(realpath --relative-to="$APPDIR/usr/venv" "$(dirname "$APP_PYTHON")")"
	python3 - "$APPDIR/usr/venv/pyvenv.cfg" "$REL_HOME" <<'PY'
from pathlib import Path
import sys
cfg = Path(sys.argv[1])
home = sys.argv[2]
lines = []
for line in cfg.read_text(encoding="utf-8").splitlines():
	if line.startswith("home "):
		lines.append(f"home = {home}")
	else:
		lines.append(line)
cfg.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
fi

echo "Installing SpaceMaker into AppDir venv…"
uv pip install --python "$VENV_PY" "$ROOT"

RAW_LINK="$(readlink "$VENV_PY" 2>/dev/null || true)"
case "$RAW_LINK" in
"" | /*)
	echo "error: AppDir python symlink must be relative: $VENV_PY -> ${RAW_LINK:-<missing>}" >&2
	exit 1
	;;
esac
RESOLVED_PY="$(readlink -f "$VENV_PY" 2>/dev/null || realpath "$VENV_PY")"
case "$RESOLVED_PY" in
"$APPDIR"/*) ;;
*)
	echo "error: AppDir python is not relocatable: $VENV_PY -> $RESOLVED_PY" >&2
	exit 1
	;;
esac
case "$RESOLVED_PY" in
*"/.local/share/uv/python/"*)
	echo "error: AppDir python still resolves into host uv cache: $RESOLVED_PY" >&2
	exit 1
	;;
esac

echo "Staging bundle metadata under usr/share/spacemaker…"
mkdir -p "$APPDIR/usr/share/spacemaker/docs"
cp -a "$ROOT/docs/legal" "$APPDIR/usr/share/spacemaker/docs/"
install -m 0644 "$ROOT/packaging/tool-catalog.json" "$APPDIR/usr/share/spacemaker/packaging/"
install -m 0644 "$ROOT/packaging/assets/spacemaker-icon.png" "$APPDIR/usr/share/spacemaker/packaging/assets/"

echo "Pruning unused PyQt6 / Qt payload…"
"$ROOT/packaging/linux-appimage/prune_pyqt6.sh" "$APPDIR/usr/venv"

echo "Smoke: CLI help…"
"$VENV_PY" -m spacemaker.desktop --help | grep -q "server-only"

echo "Smoke: offscreen WebEngine…"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
"$VENV_PY" "$ROOT/packaging/linux-appimage/smoke_webengine.py"

echo "Smoke: HTTP server…"
port="$(
	"$VENV_PY" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()'
)"
export SPACEMAKER_BUNDLE_ROOT="$APPDIR/usr/share/spacemaker"
export APPDIR="$APPDIR"
"$VENV_PY" -m spacemaker.desktop --server-only --port "${port}" &
smoke_pid=$!
trap 'kill "${smoke_pid}" 2>/dev/null || true' EXIT
ready=false
for _ in $(seq 1 60); do
	if curl -sf "http://127.0.0.1:${port}/" -o /dev/null; then
		ready=true
		break
	fi
	if ! kill -0 "${smoke_pid}" 2>/dev/null; then
		echo "error: server exited before HTTP ready" >&2
		wait "${smoke_pid}" || true
		exit 1
	fi
	sleep 0.5
done
if [[ "${ready}" != true ]]; then
	echo "error: HTTP smoke timed out" >&2
	exit 1
fi
kill "${smoke_pid}" 2>/dev/null || true
wait "${smoke_pid}" 2>/dev/null || true
trap - EXIT

echo "AppDir size: $(du -sh "$APPDIR" | cut -f1)"
echo "OK: $APPDIR"
