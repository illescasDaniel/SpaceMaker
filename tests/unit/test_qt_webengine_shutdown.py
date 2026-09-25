import pytest

from spacemaker.adapters.inbound import qt_webengine_shutdown as shutdown


qtpy = pytest.importorskip(
	"qtpy", reason="qtpy is a sys_platform == 'linux'-only dependency (see pyproject.toml); not installed here"
)
QtCore = qtpy.QtCore


def test_given_no_qapplication_when_finalize_then_does_not_raise():
	shutdown.finalize_qt_after_webview()


def test_given_no_qapplication_when_install_fix_then_does_not_raise():
	shutdown.install_qt_webengine_shutdown_fix()


def test_given_dxgi_vsync_message_when_checking_benign_then_true():
	assert shutdown._is_benign_shutdown_warning("QDxgiVSyncService not destroyed in time")


def test_given_threadstorage_message_when_checking_benign_then_true():
	message = "QThreadStorage: entry 1 destroyed before end of thread 0x15c9435f9e0"
	assert shutdown._is_benign_shutdown_warning(message)


def test_given_unrelated_warning_when_checking_benign_then_false():
	assert not shutdown._is_benign_shutdown_warning("Some other Qt warning")


def test_given_filter_installed_when_messages_logged_then_benign_swallowed_and_others_forwarded(monkeypatch):
	forwarded = []

	def fake_previous_handler(msg_type, context, message) -> None:
		forwarded.append(message)

	installed = {}

	def fake_qinstall(handler):
		previous = installed.get("handler", fake_previous_handler)
		if handler is not None:
			installed["handler"] = handler
		return previous

	monkeypatch.setattr(QtCore, "qInstallMessageHandler", fake_qinstall)

	shutdown.install_benign_shutdown_warning_filter()

	new_handler = installed["handler"]
	new_handler(QtCore.QtMsgType.QtWarningMsg, None, "QDxgiVSyncService not destroyed in time")
	new_handler(QtCore.QtMsgType.QtWarningMsg, None, "an unrelated warning")

	assert forwarded == ["an unrelated warning"]
