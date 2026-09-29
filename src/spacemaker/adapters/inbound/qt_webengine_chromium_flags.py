from __future__ import annotations

import os
import sys


_ENV_VAR = "QTWEBENGINE_CHROMIUM_FLAGS"

_SMOOTH_SCROLLING = "--enable-smooth-scrolling"
_DISABLE_GPU_COMPOSITING = "--disable-gpu-compositing"


def _default_flags() -> list[str]:
	"""Chromium flags SpaceMaker wants on its bundled Qt WebEngine.

	--enable-smooth-scrolling: Qt WebEngine ships with animated wheel scrolling off, so the
	desktop shell scrolls in abrupt line jumps while Chrome/Brave/Edge animate each notch.
	User-confirmed on Linux; plain smooth scrolling felt closest to Brave — adding
	--enable-features=WindowsScrollingPersonality (larger per-notch steps) was tried and
	not preferred.

	--disable-gpu-compositing (Windows only): works around a black/frozen WebEngine surface
	that only repaints when the window is moved or resized (same bug class as
	Chrome/Discord glitches on affected driver/GPU combinations). It disables Chromium's
	out-of-process Viz display compositor (the DXGI-shared-buffer path implicated in both
	the freeze bug and the QDxgiVSyncService/QThreadStorage shutdown warnings) while
	keeping GPU rasterization — less invasive than a full --disable-gpu.

	Dead ends already ruled out for the freeze, recorded here so they aren't retried:
	- --use-angle=d3d9 broke rendering outright (EGL "Requested version is not supported",
	cascading "context lost" errors) — WebEngine's D3D11 RHI/shared-buffer compositor path
	requires a matching D3D11 ANGLE context.
	- QSG_RHI_BACKEND=opengl had no effect. This app's QWebEngineView is plain QtWidgets
	(via pywebview's Qt backend), not a QML WebEngineView inside a QQuickWindow.
	QSG_RHI_BACKEND only governs Qt Quick's own scenegraph — it doesn't affect how
	Chromium's GPU process picks its compositor backend for a QtWidgets view. That's
	controlled separately by QTWEBENGINE_CHROMIUM_FLAGS.
	"""
	flags = [_SMOOTH_SCROLLING]
	if sys.platform == "win32":
		flags.append(_DISABLE_GPU_COMPOSITING)
	return flags


def _switch_name(flag: str) -> str:
	"""`--enable-smooth-scrolling` / `--disable-smooth-scrolling` -> `smooth-scrolling`."""
	name = flag.lstrip("-").split("=", 1)[0]
	for prefix in ("enable-", "disable-"):
		if name.startswith(prefix):
			return name[len(prefix) :]
	return name


def install_qt_webengine_chromium_flags() -> None:
	"""Merge SpaceMaker's default Chromium flags into QTWEBENGINE_CHROMIUM_FLAGS.

	Flags the user already set are kept, and a default is skipped when the user already
	chose that switch either way (e.g. `--disable-smooth-scrolling` opts out).

	Must run before Chromium/Qt Quick initializes, so call this as early as possible
	(before webview.start()/QApplication creation).
	"""
	existing = os.environ.get(_ENV_VAR, "").split()
	chosen = {_switch_name(flag) for flag in existing}
	added = [flag for flag in _default_flags() if _switch_name(flag) not in chosen]
	if added:
		os.environ[_ENV_VAR] = " ".join([*existing, *added])
