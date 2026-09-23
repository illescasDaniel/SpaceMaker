#!/usr/bin/env python3
"""Offscreen Qt WebEngine smoke test (post-prune AppDir venv)."""

from __future__ import annotations

import os
import sys


def main() -> int:
	os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
	os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

	from PyQt6.QtCore import QTimer, QUrl
	from PyQt6.QtWidgets import QApplication
	from PyQt6.QtWebEngineWidgets import QWebEngineView

	app = QApplication(sys.argv)
	view = QWebEngineView()
	loaded: list[bool] = []

	def on_load(ok: bool) -> None:
		loaded.append(ok)
		app.quit()

	view.loadFinished.connect(on_load)
	view.load(QUrl("about:blank"))
	QTimer.singleShot(30_000, app.quit)
	app.exec()
	if not loaded or not loaded[-1]:
		print("error: WebEngine failed to load about:blank", file=sys.stderr)
		return 1
	print("webengine smoke OK")
	return 0


if __name__ == "__main__":
	sys.exit(main())
