from __future__ import annotations

import sys


def _apply_native_style(app) -> None:
	from qtpy.QtWidgets import QStyleFactory

	if sys.platform == "win32":
		style = QStyleFactory.create("windows11")
	elif sys.platform.startswith("linux"):
		style = QStyleFactory.create("Fusion")
	else:
		return

	if style is not None:
		app.setStyle(style)


def install_qt_native_style() -> None:
	"""Apply a platform-appropriate QStyle so pywebview's own QtWidgets dialogs (close
	confirmation, folder pickers) look modern instead of Qt's default look.

	macOS is left alone: QtWidgets already uses the native QMacStyle by default. There is
	no QML/Qt Quick Controls anywhere in this codebase, so QT_QUICK_CONTROLS_STYLE (which
	only themes QML Qt Quick Controls components) does not apply here.
	"""
	try:
		from webview.platforms import qt as qt_platform
	except ImportError:
		return

	original_setup_app = qt_platform.setup_app

	def setup_app() -> None:
		original_setup_app()
		app = qt_platform._app
		if app is not None:
			_apply_native_style(app)

	qt_platform.setup_app = setup_app  # ty: ignore[invalid-assignment]
