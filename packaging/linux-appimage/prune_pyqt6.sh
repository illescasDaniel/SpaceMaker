#!/usr/bin/env bash
# Remove unused PyQt6 / Qt payload from an AppDir venv (keep Qt WebEngine for pywebview).
#
# Usage: prune_pyqt6.sh <venv-or-site-packages-path>
set -euo pipefail

if [[ $# -ne 1 ]]; then
	echo "usage: $0 <venv-or-site-packages-path>" >&2
	exit 2
fi

TARGET="$1"
if [[ ! -d "$TARGET" ]]; then
	echo "error: not a directory: $TARGET" >&2
	exit 1
fi

SITE=""
if [[ -d "$TARGET/PyQt6" ]]; then
	SITE="$TARGET"
else
	shopt -s nullglob
	candidates=("$TARGET"/lib/python*/site-packages)
	shopt -u nullglob
	if [[ ${#candidates[@]} -eq 0 ]]; then
		echo "error: no site-packages under $TARGET" >&2
		exit 1
	fi
	SITE="${candidates[0]}"
fi

PYQT="$SITE/PyQt6"
if [[ ! -d "$PYQT" ]]; then
	echo "error: PyQt6 not found at $PYQT" >&2
	exit 1
fi

BEFORE_BYTES=""
if du_out="$(du -sk "$PYQT" 2>/dev/null)"; then
	BEFORE_BYTES="$(awk '{print $1 * 1024}' <<<"$du_out")"
fi
echo "Pruning PyQt6 under $PYQT (before: $(du -sh "$PYQT" 2>/dev/null | cut -f1 || echo unknown))…"

rm_rf() {
	local path
	for path in "$@"; do
		if [[ -e "$path" || -L "$path" ]]; then
			rm -rf "$path"
		fi
	done
}

rm_rf \
	"$PYQT/assistant" \
	"$PYQT/designer" \
	"$PYQT/linguist" \
	"$PYQT/lupdate" \
	"$PYQT/lrelease" \
	"$PYQT/qmlls" \
	"$PYQT/qmllint" \
	"$PYQT/qmlformat" \
	"$PYQT/qsb" \
	"$PYQT/balsam" \
	"$PYQT/balsamui" \
	"$PYQT/doc" \
	"$PYQT/include" \
	"$PYQT/typesystems" \
	"$PYQT/glue" \
	"$PYQT/metatypes" \
	"$PYQT/Qt/metatypes" \
	"$PYQT/Qt/libexec" \
	"$PYQT/lib" \
	"$PYQT/scripts" \
	"$PYQT/support" \
	"$PYQT/QtAsyncio" \
	"$PYQT/py.typed" \
	"$PYQT/__feature__.pyi" \
	"$PYQT/_git_pyside_version.py"

shopt -s nullglob
rm_rf "$PYQT"/*.pyi
KEEP_BINDINGS=(
	QtCore
	QtGui
	QtWidgets
	QtNetwork
	QtWebChannel
	QtWebEngineCore
	QtWebEngineWidgets
	QtPrintSupport
	QtOpenGL
	QtDBus
)
keep_binding() {
	local name="$1"
	local keep
	for keep in "${KEEP_BINDINGS[@]}"; do
		if [[ "$name" == "$keep" ]]; then
			return 0
		fi
	done
	return 1
}
for so in "$PYQT"/*.abi3.so; do
	base="$(basename "$so" .abi3.so)"
	if ! keep_binding "$base"; then
		rm_rf "$so"
	fi
done
shopt -u nullglob

QT_LIB="$PYQT/Qt/lib"
if [[ -d "$QT_LIB" ]]; then
	shopt -s nullglob
	for lib in "$QT_LIB"/libQt6*.so* "$QT_LIB"/libav*.so* "$QT_LIB"/libQt6FFmpegStub*; do
		base="$(basename "$lib")"
		case "$base" in
		libQt6Core.so* | libQt6Gui.so* | libQt6Widgets.so* | libQt6DBus.so* | libQt6Network.so* | \
			libQt6OpenGL.so* | libQt6PrintSupport.so* | \
			libQt6WebChannel.so* | libQt6WebEngineCore.so* | libQt6WebEngineWidgets.so* | \
			libQt6XcbQpa.so* | libQt6EglFSDeviceIntegration.so* | libQt6EglFsKmsSupport.so* | \
			libQt6WaylandClient.so* | libQt6WlShellIntegration.so* | \
			libQt6WaylandEglClientHwIntegration.so* | \
			libicudata.so* | libicui18n.so* | libicuuc.so* | libQt6Positioning.so* | libQt6Quick.so*) ;;
		*)
			rm_rf "$lib"
			;;
		esac
	done
	shopt -u nullglob
fi

QML="$PYQT/Qt/qml"
if [[ -d "$QML" ]]; then
	rm_rf \
		"$QML/Qt3D" \
		"$QML/Qt5Compat" \
		"$QML/QtCharts" \
		"$QML/QtDataVisualization" \
		"$QML/QtGraphs" \
		"$QML/QtLocation" \
		"$QML/QtMultimedia" \
		"$QML/QtPositioning" \
		"$QML/QtQuick3D" \
		"$QML/QtRemoteObjects" \
		"$QML/QtScxml" \
		"$QML/QtSensors" \
		"$QML/QtTest" \
		"$QML/QtTextToSpeech" \
		"$QML/QtWayland"
	# Keep QtWebEngine, QtWebChannel, QtQuick (WebEngine deps), QtQuick/Controls subset.
	if [[ -d "$QML/QtQuick" ]]; then
		rm_rf \
			"$QML/QtQuick/Particles" \
			"$QML/QtQuick/Pdf" \
			"$QML/QtQuick/Scene2D" \
			"$QML/QtQuick/Scene3D" \
			"$QML/QtQuick/LocalStorage" \
			"$QML/QtQuick/Timeline" \
			"$QML/QtQuick/VectorImage" \
			"$QML/QtQuick/VirtualKeyboard" \
			"$QML/QtQuick/tooling" \
			"$QML/QtQuick/Controls/designer"
	fi
fi

PLUGINS="$PYQT/Qt/plugins"
if [[ -d "$PLUGINS" ]]; then
	rm_rf \
		"$PLUGINS/assetimporters" \
		"$PLUGINS/canbus" \
		"$PLUGINS/designer" \
		"$PLUGINS/geometryloaders" \
		"$PLUGINS/geoservices" \
		"$PLUGINS/multimedia" \
		"$PLUGINS/position" \
		"$PLUGINS/qmllint" \
		"$PLUGINS/qmltooling" \
		"$PLUGINS/renderers" \
		"$PLUGINS/renderplugins" \
		"$PLUGINS/sceneparsers" \
		"$PLUGINS/scxmldatamodel" \
		"$PLUGINS/sensors" \
		"$PLUGINS/sqldrivers" \
		"$PLUGINS/texttospeech" \
		"$PLUGINS/vectorimageformats"
fi

if command -v strip >/dev/null 2>&1; then
	shopt -s nullglob
	for so in "$PYQT"/*.abi3.so "$PYQT"/Qt/lib/*.so* "$PYQT"/Qt/plugins/*/*.so "$PYQT"/Qt/qml/*/*.so "$PYQT"/Qt/qml/*/*/*.so; do
		if [[ -f "$so" && ! -L "$so" ]]; then
			strip --strip-unneeded "$so" 2>/dev/null || true
		fi
	done
	shopt -u nullglob
fi

AFTER_BYTES=""
if du_out="$(du -sk "$PYQT" 2>/dev/null)"; then
	AFTER_BYTES="$(awk '{print $1 * 1024}' <<<"$du_out")"
fi
AFTER_HUMAN="$(du -sh "$PYQT" 2>/dev/null | cut -f1 || echo unknown)"
if [[ -n "${BEFORE_BYTES:-}" && -n "${AFTER_BYTES:-}" && "$BEFORE_BYTES" =~ ^[0-9]+$ && "$AFTER_BYTES" =~ ^[0-9]+$ ]]; then
	SAVED=$((BEFORE_BYTES - AFTER_BYTES))
	echo "Pruned PyQt6 to $AFTER_HUMAN (saved $((SAVED / 1024 / 1024)) MiB)."
else
	echo "Pruned PyQt6 to $AFTER_HUMAN."
fi
