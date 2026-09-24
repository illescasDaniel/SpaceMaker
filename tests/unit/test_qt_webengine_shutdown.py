from spacemaker.adapters.inbound import qt_webengine_shutdown as shutdown


def test_given_no_qapplication_when_finalize_then_does_not_raise():
	shutdown.finalize_qt_after_webview()


def test_given_no_qapplication_when_install_fix_then_does_not_raise():
	shutdown.install_qt_webengine_shutdown_fix()
