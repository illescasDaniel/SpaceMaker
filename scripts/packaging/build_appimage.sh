#!/usr/bin/env bash
# Linux AppImage from pruned AppDir venv. Output: dist/*.AppImage + SHA256SUMS

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

APPDIR="${APPDIR:-${repo}/build/SpaceMaker.AppDir}"
APPIMAGETOOL_VERSION="${APPIMAGETOOL_VERSION:-1.9.1}"
APPIMAGETOOL_URL="${APPIMAGETOOL_URL:-https://github.com/AppImage/appimagetool/releases/download/${APPIMAGETOOL_VERSION}/appimagetool-${app_arch}.AppImage}"
APPIMAGETOOL_SHA256="${APPIMAGETOOL_SHA256:-ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0}"

bash "${repo}/packaging/linux-appimage/build-appdir.sh"

version="$(uv run python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')"

install -m 0644 "${repo}/packaging/assets/spacemaker-icon.png" "${APPDIR}/spacemaker.png"
cp "${APPDIR}/spacemaker.png" "${APPDIR}/.DirIcon"

cat >"${APPDIR}/spacemaker.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=SpaceMaker
GenericName=Phone media backup
Comment=Local backup, convert, and gallery for phone media
Exec=AppRun
Icon=spacemaker
Categories=Utility;
Terminal=false
StartupWMClass=SpaceMaker
X-AppImage-Version=${version}
X-AppImage-Publisher=Daniel Illescas Romero
EOF

cat >"${APPDIR}/AppRun" <<'EOF'
#!/bin/sh
set -eu
unset ARGV0
HERE="$(dirname "$(readlink -f "$0")")"
export APPDIR="$HERE"
export SPACEMAKER_BUNDLE_ROOT="$HERE/usr/share/spacemaker"
export PATH="$HERE/usr/venv/bin:${PATH:-}"
export PYTHONNOUSERSITE=1
exec "$HERE/usr/venv/bin/python" -m spacemaker.desktop "$@"
EOF
chmod +x "${APPDIR}/AppRun"

tool="${repo}/build/appimagetool-${app_arch}.AppImage"
NEED_FETCH=0
if [[ ! -x "${tool}" ]]; then
	NEED_FETCH=1
elif [[ -n "${APPIMAGETOOL_SHA256}" ]]; then
	ACTUAL="$(sha256sum "${tool}" | awk '{print $1}')"
	if [[ "${ACTUAL}" != "${APPIMAGETOOL_SHA256}" ]]; then
		echo "appimagetool digest mismatch; re-fetching…"
		NEED_FETCH=1
	fi
fi
if [[ "${NEED_FETCH}" -eq 1 ]]; then
	mkdir -p "${repo}/build"
	echo "Fetching appimagetool ${APPIMAGETOOL_VERSION}…"
	curl -fsSL -o "${tool}" "${APPIMAGETOOL_URL}"
	chmod +x "${tool}"
fi
if [[ -n "${APPIMAGETOOL_SHA256}" ]]; then
	echo "${APPIMAGETOOL_SHA256}  ${tool}" | sha256sum -c -
fi

out="${repo}/dist/SpaceMaker-${version}-${app_arch}.AppImage"
rm -f "${out}"
echo "AppDir size before pack: $(du -sh "${APPDIR}" | cut -f1)"
echo "Packing ${out} (squashfs zstd compression-level 19)…"
ARCH="${app_arch}" VERSION="${version}" APPIMAGE_EXTRACT_AND_RUN=1 "${tool}" \
	--mksquashfs-opt -Xcompression-level \
	--mksquashfs-opt 19 \
	"${APPDIR}" "${out}"
chmod +x "${out}"
echo "Built ${out} ($(du -h "${out}" | cut -f1))"

(
	cd "${repo}/dist"
	sha256sum "$(basename "${out}")" >SHA256SUMS
)
echo "Wrote ${repo}/dist/SHA256SUMS"

echo "OK: ${out}"
