#!/usr/bin/env bash
# Linux AppImage wrapper around the PyInstaller onefile binary. Output: dist/*.AppImage

set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo}"

if [[ "$(uname -s)" != "Linux" ]]; then
	echo "error: AppImage builds are supported on Linux only" >&2
	exit 1
fi

arch="$(uname -m)"
case "${arch}" in
x86_64) app_arch="x86_64" ;;
aarch64 | arm64) app_arch="aarch64" ;;
*)
	echo "error: unsupported CPU architecture: ${arch}" >&2
	exit 1
	;;
esac

tool_arch="${app_arch}"
if [[ "${app_arch}" == "aarch64" ]]; then
	tool_arch="aarch64"
fi

echo "Syncing brand icons…"
uv run python scripts/packaging/sync_brand_icons.py

echo "Building PyInstaller binary…"
bash scripts/packaging/build_installer.sh

version="$(uv run python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')"
appdir="${repo}/build/SpaceMaker.AppDir"
rm -rf "${appdir}"
mkdir -p "${appdir}/usr/bin"

install -m 0755 "${repo}/dist/SpaceMaker" "${appdir}/usr/bin/SpaceMaker"
install -m 0644 "${repo}/packaging/assets/spacemaker-icon.png" "${appdir}/spacemaker.png"
cp "${appdir}/spacemaker.png" "${appdir}/.DirIcon"

cat >"${appdir}/spacemaker.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=SpaceMaker
GenericName=Phone media backup
Comment=Local backup, convert, and gallery for phone media
Exec=SpaceMaker
Icon=spacemaker
Categories=Utility;Photography;AudioVideo;
Terminal=false
StartupWMClass=SpaceMaker
EOF

cat >"${appdir}/AppRun" <<'EOF'
#!/bin/sh
unset ARGV0
HERE="$(dirname "$(readlink -f "$0")")"
export PATH="${HERE}/usr/bin:${PATH}"
exec "${HERE}/usr/bin/SpaceMaker" "$@"
EOF
chmod +x "${appdir}/AppRun"
ln -sf usr/bin/SpaceMaker "${appdir}/SpaceMaker"

tool="${repo}/build/appimagetool-${tool_arch}.AppImage"
if [[ ! -x "${tool}" ]]; then
	mkdir -p "${repo}/build"
	url="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-${tool_arch}.AppImage"
	echo "Downloading appimagetool…"
	curl -fsSL -o "${tool}" "${url}"
	chmod +x "${tool}"
fi

out="${repo}/dist/SpaceMaker-${version}-${app_arch}.AppImage"
rm -f "${out}"
ARCH="${app_arch}" "${tool}" "${appdir}" "${out}"

if [[ ! -f "${out}" ]]; then
	echo "error: AppImage missing: ${out}" >&2
	exit 1
fi

echo "OK: ${out} ($(du -h "${out}" | cut -f1))"
