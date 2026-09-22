from __future__ import annotations

import logging


logger = logging.getLogger(__name__)


def _drain_qt_events(app, *, rounds: int = 20) -> None:
	from qtpy import QtCore

	for _ in range(rounds):
		app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)


def _tear_down_webview(view) -> None:
	page = view.webview.page()
	if page is not None:
		view.webview.setPage(None)
		page.deleteLater()
	profile = getattr(view, "profile", None)
	if profile is not None:
		view.profile = None
		profile.deleteLater()


def install_qt_webengine_shutdown_fix() -> None:
	"""Delete WebEngine pages before their profile is released on app quit."""
	try:
		from qtpy import QtCore
		from webview.platforms import qt as qt_platform
	except ImportError:
		return

	if not getattr(qt_platform, "is_webengine", False):
		return

	def close_event(self, event) -> None:
		should_cancel = self.pywebview_window.events.closing.set()
		if should_cancel:
			event.ignore()
			return

		if self.pywebview_window.confirm_close:
			from qtpy.QtWidgets import QMessageBox

			yes = QMessageBox.StandardButton.Yes
			no = QMessageBox.StandardButton.No
			reply = QMessageBox.question(self, self.title, self.localization["global.quitConfirmation"], yes, no)
			if reply == no:
				event.ignore()
				return

		event.accept()

		if self.uid in qt_platform.BrowserView.instances:
			del qt_platform.BrowserView.instances[self.uid]

		if self.pywebview_window in qt_platform.windows:
			qt_platform.windows.remove(self.pywebview_window)

		self.pywebview_window.events.closed.set()
		_tear_down_webview(self)

		if len(qt_platform.BrowserView.instances) == 0:
			self.hide()
			app = qt_platform._app
			if app is not None:

				def finish_quit() -> None:
					_drain_qt_events(app)
					app.quit()

				QtCore.QTimer.singleShot(200, finish_quit)

	original_setup_app = qt_platform.setup_app

	def setup_app() -> None:
		original_setup_app()
		app = qt_platform._app
		if app is None:
			return

		def on_about_to_quit() -> None:
			for browser in list(qt_platform.BrowserView.instances.values()):
				_tear_down_webview(browser)
			_drain_qt_events(app)

		app.aboutToQuit.connect(on_about_to_quit)

	qt_platform.setup_app = setup_app  # ty: ignore[invalid-assignment]
	qt_platform.BrowserView.closeEvent = close_event
	logger.debug("Installed Qt WebEngine shutdown fix")
