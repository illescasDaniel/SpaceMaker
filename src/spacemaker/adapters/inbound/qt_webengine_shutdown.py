from __future__ import annotations

import contextlib
import logging
import sys
import time


logger = logging.getLogger(__name__)


def _shutdown_event_rounds() -> int:
	return 80 if sys.platform == "win32" else 25


def _shutdown_quit_delay_ms() -> int:
	return 650 if sys.platform == "win32" else 200


def _shutdown_finalize_passes() -> int:
	return 6 if sys.platform == "win32" else 3


def _drain_qt_events(app, *, rounds: int | None = None) -> None:
	from qtpy import QtCore

	count = _shutdown_event_rounds() if rounds is None else rounds
	for _ in range(count):
		app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)


def _disconnect_signal(source, signal_name: str, slot) -> None:
	signal = getattr(source, signal_name, None)
	if signal is None:
		return
	with contextlib.suppress(TypeError, RuntimeError):
		signal.disconnect(slot)


def _disconnect_webengine_bindings(view, webview_widget, page, profile) -> None:
	if page is not None:
		_disconnect_signal(page, "loadFinished", view.on_load_finished)
		if hasattr(page, "featurePermissionRequested"):
			_disconnect_signal(page, "featurePermissionRequested", page.onFeaturePermissionRequested)

	if profile is not None:
		cookie_store = profile.cookieStore()
		_disconnect_signal(cookie_store, "cookieAdded", view.on_cookie_added)
		_disconnect_signal(cookie_store, "cookieRemoved", view.on_cookie_removed)
		with contextlib.suppress(TypeError, RuntimeError):
			profile.downloadRequested.disconnect(view.on_download_requested)


def _delete_top_level_widgets(app) -> None:
	from qtpy.QtWidgets import QApplication, QWidget

	for widget in list(QApplication.topLevelWidgets()):
		if widget is None:
			continue
		with contextlib.suppress(Exception):
			widget.hide()
		if isinstance(widget, QWidget):
			widget.deleteLater()
	_drain_qt_events(app)


def _tear_down_webview(view, app=None) -> None:
	if getattr(view, "_spacemaker_webengine_torn_down", False):
		return
	view._spacemaker_webengine_torn_down = True

	webview_widget = getattr(view, "webview", None)
	if webview_widget is None:
		return

	page = webview_widget.page()
	profile = getattr(view, "profile", None)
	if page is not None:
		_disconnect_webengine_bindings(view, webview_widget, page, profile)

		nav = getattr(page, "nav_handler", None)
		if nav is not None:
			page.nav_handler = None
			nav.setParent(None)
			nav.deleteLater()

		channel = getattr(view, "channel", None)
		if channel is not None:
			with contextlib.suppress(Exception):
				page.setWebChannel(None)
			view.channel = None
			channel.setParent(None)
			channel.deleteLater()

		webview_widget.setPage(None)
		page.deleteLater()

	if app is not None:
		_drain_qt_events(app)

	if profile is not None:
		view.profile = None
		with contextlib.suppress(Exception):
			profile.setUrlRequestInterceptor(None)
		profile.deleteLater()

	interceptor = getattr(view, "request_interceptor", None)
	if interceptor is not None:
		view.request_interceptor = None
		interceptor.deleteLater()

	if app is not None:
		_drain_qt_events(app)

	view.setCentralWidget(None)
	webview_widget.deleteLater()
	view.hide()
	view.deleteLater()


def finalize_qt_after_webview() -> None:
	"""Let WebEngine/Chromium finish teardown after pywebview's event loop exits."""
	try:
		from qtpy import QtCore
		from qtpy.QtWidgets import QApplication
	except ImportError:
		return

	app = QApplication.instance()
	if app is None:
		return

	_delete_top_level_widgets(app)
	for _ in range(_shutdown_finalize_passes()):
		_drain_qt_events(app)
		if sys.platform == "win32":
			time.sleep(0.08)
			app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 150)

	if sys.platform == "win32":
		# QDxgiVSyncService shuts down asynchronously after the last native window goes away.
		time.sleep(0.2)
		_drain_qt_events(app, rounds=40)


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
		app = qt_platform._app
		_tear_down_webview(self, app)

		if len(qt_platform.BrowserView.instances) == 0:
			if app is not None:

				def finish_quit() -> None:
					for browser in list(qt_platform.BrowserView.instances.values()):
						_tear_down_webview(browser, app)
					_delete_top_level_widgets(app)
					_drain_qt_events(app)
					if sys.platform == "win32":
						time.sleep(0.15)
						_drain_qt_events(app, rounds=35)
					app.quit()

				QtCore.QTimer.singleShot(_shutdown_quit_delay_ms(), finish_quit)

	original_setup_app = qt_platform.setup_app

	def setup_app() -> None:
		original_setup_app()
		app = qt_platform._app
		if app is None:
			return

		def on_about_to_quit() -> None:
			for browser in list(qt_platform.BrowserView.instances.values()):
				_tear_down_webview(browser, app)
			_delete_top_level_widgets(app)
			_drain_qt_events(app)

		app.aboutToQuit.connect(on_about_to_quit)

	qt_platform.setup_app = setup_app  # ty: ignore[invalid-assignment]
	qt_platform.BrowserView.closeEvent = close_event
	logger.debug("Installed Qt WebEngine shutdown fix")
