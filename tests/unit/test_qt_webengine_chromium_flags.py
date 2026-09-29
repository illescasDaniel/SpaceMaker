from spacemaker.adapters.inbound import qt_webengine_chromium_flags as chromium_flags


ENV_VAR = "QTWEBENGINE_CHROMIUM_FLAGS"


def test_given_win32_when_install_then_sets_smooth_scrolling_and_disable_gpu_compositing(monkeypatch):
	monkeypatch.setattr(chromium_flags.sys, "platform", "win32")
	monkeypatch.delenv(ENV_VAR, raising=False)

	chromium_flags.install_qt_webengine_chromium_flags()

	assert chromium_flags.os.environ[ENV_VAR] == "--enable-smooth-scrolling --disable-gpu-compositing"


def test_given_linux_when_install_then_sets_only_smooth_scrolling(monkeypatch):
	monkeypatch.setattr(chromium_flags.sys, "platform", "linux")
	monkeypatch.delenv(ENV_VAR, raising=False)

	chromium_flags.install_qt_webengine_chromium_flags()

	assert chromium_flags.os.environ[ENV_VAR] == "--enable-smooth-scrolling"


def test_given_existing_flag_when_install_then_keeps_it_and_appends_defaults(monkeypatch):
	monkeypatch.setattr(chromium_flags.sys, "platform", "win32")
	monkeypatch.setenv(ENV_VAR, "--some-other-flag")

	chromium_flags.install_qt_webengine_chromium_flags()

	assert chromium_flags.os.environ[ENV_VAR] == "--some-other-flag --enable-smooth-scrolling --disable-gpu-compositing"


def test_given_user_disabled_smooth_scrolling_when_install_then_respects_opt_out(monkeypatch):
	monkeypatch.setattr(chromium_flags.sys, "platform", "linux")
	monkeypatch.setenv(ENV_VAR, "--disable-smooth-scrolling")

	chromium_flags.install_qt_webengine_chromium_flags()

	assert chromium_flags.os.environ[ENV_VAR] == "--disable-smooth-scrolling"


def test_given_defaults_already_present_when_install_twice_then_does_not_duplicate(monkeypatch):
	monkeypatch.setattr(chromium_flags.sys, "platform", "win32")
	monkeypatch.delenv(ENV_VAR, raising=False)

	chromium_flags.install_qt_webengine_chromium_flags()
	chromium_flags.install_qt_webengine_chromium_flags()

	assert chromium_flags.os.environ[ENV_VAR] == "--enable-smooth-scrolling --disable-gpu-compositing"
