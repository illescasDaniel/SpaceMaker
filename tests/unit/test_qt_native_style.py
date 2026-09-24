from spacemaker.adapters.inbound import qt_native_style as native_style


def test_given_no_webview_qt_platform_when_install_then_does_not_raise():
	native_style.install_qt_native_style()
