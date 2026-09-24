from spacemaker.adapters.inbound import qt_webengine_gpu_flags as gpu_flags


def test_given_win32_when_install_then_sets_disable_gpu_compositing_flag(monkeypatch):
	monkeypatch.setattr(gpu_flags.sys, "platform", "win32")
	monkeypatch.delenv("QTWEBENGINE_CHROMIUM_FLAGS", raising=False)

	gpu_flags.install_qt_webengine_gpu_flags()

	assert gpu_flags.os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] == "--disable-gpu-compositing"


def test_given_win32_and_existing_flag_when_install_then_does_not_clobber_it(monkeypatch):
	monkeypatch.setattr(gpu_flags.sys, "platform", "win32")
	monkeypatch.setenv("QTWEBENGINE_CHROMIUM_FLAGS", "--some-other-flag")

	gpu_flags.install_qt_webengine_gpu_flags()

	assert gpu_flags.os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] == "--some-other-flag"


def test_given_non_win32_when_install_then_does_not_set_flag(monkeypatch):
	monkeypatch.setattr(gpu_flags.sys, "platform", "linux")
	monkeypatch.delenv("QTWEBENGINE_CHROMIUM_FLAGS", raising=False)

	gpu_flags.install_qt_webengine_gpu_flags()

	assert "QTWEBENGINE_CHROMIUM_FLAGS" not in gpu_flags.os.environ
