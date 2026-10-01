#!/usr/bin/env bash
# macOS DMG with SpaceMaker.app (PyInstaller onedir + BUNDLE). Output: dist/*.dmg + SHA256SUMS

set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo}"

if [[ "$(uname -s)" != "Darwin" ]]; then
	echo "error: macOS DMG builds are supported on Darwin only" >&2
	exit 1
fi

arch="$(uname -m)"
case "${arch}" in
arm64) dmg_arch="arm64" ;;
x86_64) dmg_arch="x86_64" ;;
*)
	echo "error: unsupported CPU architecture: ${arch}" >&2
	exit 1
	;;
esac

echo "Syncing dev dependencies (includes PyInstaller)…"
uv sync --group dev

echo "Syncing brand icons (PNG + .icns)…"
uv run python scripts/packaging/sync_brand_icons.py
if [[ ! -f "${repo}/packaging/assets/spacemaker.icns" ]]; then
	echo "error: expected packaging/assets/spacemaker.icns after icon sync" >&2
	exit 1
fi

echo "Building SpaceMaker.app in dist/…"
uv run pyinstaller packaging/spacemaker.spec --noconfirm

app="${repo}/dist/SpaceMaker.app"
bin="${app}/Contents/MacOS/SpaceMaker"
if [[ ! -d "${app}" ]]; then
	echo "error: expected app bundle missing: ${app}" >&2
	exit 1
fi
if [[ ! -x "${bin}" ]]; then
	echo "error: expected MacOS binary missing: ${bin}" >&2
	exit 1
fi

echo "Ad-hoc codesign…"
codesign --force --deep -s - "${app}"

version="$(uv run python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')"
dmg_name="SpaceMaker-${version}-${dmg_arch}.dmg"
out="${repo}/dist/${dmg_name}"

stage="$(mktemp -d "${TMPDIR:-/tmp}/spacemaker-dmg-XXXXXX")"
cleanup() {
	rm -rf "${stage}"
}
trap cleanup EXIT

echo "Staging DMG contents…"
cp -R "${app}" "${stage}/SpaceMaker.app"
ln -s /Applications "${stage}/Applications"

rm -f "${out}"
echo "Creating ${out}…"
hdiutil create \
	-volname "SpaceMaker" \
	-srcfolder "${stage}" \
	-ov \
	-format UDZO \
	"${out}"

(
	cd "${repo}/dist"
	shasum -a 256 "${dmg_name}" >SHA256SUMS
)
echo "Wrote ${repo}/dist/SHA256SUMS"

echo "Smoke test: --help and --server-only HTTP…"
if ! "${bin}" --help 2>&1 | grep -q "server-only"; then
	echo "error: --help did not print expected usage" >&2
	exit 1
fi

port="$(
	uv run python -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()'
)"
"${bin}" --server-only --port "${port}" &
smoke_pid=$!
trap 'kill "${smoke_pid}" 2>/dev/null || true; cleanup' EXIT

ready=false
for _ in $(seq 1 90); do
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
trap cleanup EXIT

echo "OK: ${out} ($(du -h "${out}" | cut -f1))"
echo "OK: ${app} ($(du -sh "${app}" | cut -f1))"
