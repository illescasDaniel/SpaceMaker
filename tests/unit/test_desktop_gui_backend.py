from spacemaker import desktop


def test_given_win32_when_default_gui_backend_then_edgechromium(monkeypatch):
	monkeypatch.setattr(desktop.sys, "platform", "win32")

	assert desktop._default_gui_backend() == "edgechromium"


def test_given_darwin_when_default_gui_backend_then_cocoa(monkeypatch):
	monkeypatch.setattr(desktop.sys, "platform", "darwin")

	assert desktop._default_gui_backend() == "cocoa"


def test_given_linux_when_default_gui_backend_then_qt(monkeypatch):
	monkeypatch.setattr(desktop.sys, "platform", "linux")

	assert desktop._default_gui_backend() == "qt"
