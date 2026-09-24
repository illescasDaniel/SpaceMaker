from __future__ import annotations

import os
import sys


def install_qt_webengine_gpu_flags() -> None:
	"""Windows: work around a black/frozen WebEngine surface that only repaints when the
	window is moved or resized (same bug class as Chrome/Discord glitches on affected
	driver/GPU combinations).

	Dead ends already ruled out, recorded here so they aren't retried:
	- QTWEBENGINE_CHROMIUM_FLAGS=--use-angle=d3d9 broke rendering outright (EGL
	"Requested version is not supported", cascading "context lost" errors) — WebEngine's
	D3D11 RHI/shared-buffer compositor path requires a matching D3D11 ANGLE context.
	- QSG_RHI_BACKEND=opengl had no effect. This app's QWebEngineView is plain QtWidgets
	(via pywebview's Qt backend), not a QML WebEngineView inside a QQuickWindow.
	QSG_RHI_BACKEND only governs Qt Quick's own scenegraph — it doesn't affect how
	Chromium's GPU process picks its compositor backend for a QtWidgets view. That's
	controlled separately by QTWEBENGINE_CHROMIUM_FLAGS.

	Next experiment: --disable-gpu-compositing disables Chromium's out-of-process Viz
	display compositor (the DXGI-shared-buffer path implicated in both the freeze bug and
	the QDxgiVSyncService/QThreadStorage shutdown warnings) while keeping GPU
	rasterization — less invasive than a full --disable-gpu.

	Must run before Chromium/Qt Quick initializes, so call this as early as possible
	(before webview.start()/QApplication creation).
	"""
	if sys.platform != "win32":
		return
	os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu-compositing")
