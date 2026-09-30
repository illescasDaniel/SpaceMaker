import json
import sys
from pathlib import Path

from spacemaker.bootstrap import platform_setup_hints
from spacemaker.bootstrap.bundled_tools import BundledTool, bundled_tool_path
from spacemaker.bootstrap.services.managed_tools import ManagedToolsService
from spacemaker.ports.outbound.tool_installer import ToolInstallResult


_REPO = Path(__file__).resolve().parents[2]


def test_given_macos_catalog_when_loaded_then_no_static_ffmpeg_wheel():
	# given
	catalog = json.loads((_REPO / "packaging" / "tool-catalog.json").read_text(encoding="utf-8"))
	# when / then
	for key in ("macos-aarch64", "macos-x86_64"):
		platform = catalog["platforms"][key]
		assert platform.get("ffmpeg") is None


def test_given_missing_ffmpeg_on_macos_when_hint_then_brew_install_ffmpeg():
	# given / when
	cmd = platform_setup_hints.install_command_for_tool(
		"ffmpeg",
		phase="failed",
		resolution="missing",
		platform="darwin",
	)
	# then
	assert cmd == "brew install ffmpeg"


def test_given_missing_magick_on_macos_when_hint_then_brew_imagemagick():
	# given / when
	cmd = platform_setup_hints.install_command_for_tool(
		"magick",
		phase="idle",
		resolution="missing",
		platform="darwin",
	)
	# then
	assert cmd == "brew install imagemagick"


def test_given_missing_exiftool_on_macos_when_hint_then_brew_exiftool():
	# given / when
	cmd = platform_setup_hints.install_command_for_tool(
		"exiftool",
		phase="idle",
		resolution="missing",
		platform="darwin",
	)
	# then
	assert cmd == "brew install exiftool"


def test_given_missing_magick_on_windows_when_hint_then_winget_imagemagick():
	# given / when
	cmd = platform_setup_hints.install_command_for_tool(
		"magick",
		phase="idle",
		resolution="missing",
		platform="win32",
	)
	# then
	assert cmd is not None
	assert "winget install" in cmd
	assert "ImageMagick.ImageMagick" in cmd


def test_given_ready_managed_when_hint_then_none():
	# given / when
	cmd = platform_setup_hints.install_command_for_tool(
		"adb",
		phase="ready",
		resolution="managed",
		platform="darwin",
	)
	# then
	assert cmd is None


def test_given_ubuntu_os_release_when_detect_then_apt():
	# given
	text = "ID=ubuntu\nID_LIKE=debian\n"
	# when
	family = platform_setup_hints.detect_linux_package_family(
		os_release_text=text,
		which=lambda _name: None,
	)
	# then
	assert family == "apt"


def test_given_apt_family_when_avifenc_failed_then_apt_libavif_bin():
	# given / when
	cmd = platform_setup_hints.install_command_for_tool(
		"avifenc",
		phase="failed",
		resolution="missing",
		platform="linux",
		linux_family="apt",
	)
	# then
	assert cmd == "sudo apt install libavif-bin"


def test_given_fedora_when_ffmpeg_failed_then_dnf_hint():
	# given / when
	cmd = platform_setup_hints.install_command_for_tool(
		"ffmpeg",
		phase="failed",
		resolution="missing",
		platform="linux",
		linux_family="dnf",
	)
	# then
	assert cmd == "sudo dnf install ffmpeg"


def test_given_arch_with_paru_when_magick_missing_then_paru_hint():
	# given / when
	cmd = platform_setup_hints.install_command_for_tool(
		"magick",
		phase="idle",
		resolution="missing",
		platform="linux",
		linux_family="arch",
		arch_prefix="paru -S",
	)
	# then
	assert cmd == "paru -S imagemagick"


def test_given_missing_macos_tools_when_bulk_then_brew_deduped():
	# given / when
	cmd = platform_setup_hints.install_all_command(
		["ffmpeg", "ffprobe", "magick", "exiftool"],
		platform="darwin",
	)
	# then
	assert cmd == "brew install ffmpeg imagemagick exiftool"


def test_given_missing_windows_tools_when_bulk_then_winget_multiline():
	# given / when
	cmd = platform_setup_hints.install_all_command(
		["magick", "exiftool"],
		platform="win32",
	)
	# then
	assert cmd is not None
	assert "ImageMagick.ImageMagick" in cmd
	assert "OliverBetz.ExifTool" in cmd
	assert "\n" in cmd


def test_given_brew_missing_when_pm_command_then_homebrew_install():
	# given / when
	cmd = platform_setup_hints.package_manager_command(
		platform="darwin",
		which=lambda _name: None,
	)
	# then
	assert cmd is not None
	assert "Homebrew/install" in cmd


def test_given_brew_present_when_pm_command_then_none():
	# given / when
	cmd = platform_setup_hints.package_manager_command(
		platform="darwin",
		which=lambda name: "/opt/homebrew/bin/brew" if name == "brew" else None,
	)
	# then
	assert cmd is None


def test_given_unknown_linux_when_failed_then_no_hint():
	# given / when
	cmd = platform_setup_hints.install_command_for_tool(
		"ffmpeg",
		phase="failed",
		resolution="missing",
		platform="linux",
		os_release_text="ID=obscureos\n",
		which=lambda _name: None,
	)
	# then
	assert cmd is None


def test_given_failed_adb_on_macos_when_hint_then_brew_platform_tools():
	# given / when
	cmd = platform_setup_hints.install_command_for_tool(
		"adb",
		phase="failed",
		resolution="missing",
		platform="darwin",
	)
	# then
	assert cmd == "brew install android-platform-tools"


def test_given_linux_when_iphone_hint_then_true():
	# given / when / then
	assert platform_setup_hints.show_iphone_usb_hint(platform="linux") is True
	assert platform_setup_hints.show_iphone_usb_hint(platform="darwin") is False
	assert platform_setup_hints.show_iphone_usb_hint(platform="win32") is False


def test_given_missing_tools_on_macos_when_status_dict_then_per_tool_brew_and_bulk(
	tmp_path: Path,
	monkeypatch,
):
	# given
	monkeypatch.setattr(sys, "platform", "darwin")
	monkeypatch.setenv("SPACEMAKER_TOOLS_DIR", str(tmp_path))

	def fake_which(name: str) -> str | None:
		if name == "brew":
			return "/opt/homebrew/bin/brew"
		return None

	monkeypatch.setattr(platform_setup_hints.shutil, "which", fake_which)
	monkeypatch.setattr("spacemaker.bootstrap.bundled_tools.shutil.which", fake_which)
	monkeypatch.setattr("spacemaker.bootstrap.bundled_tools.host_tool_path_dirs", lambda: [])

	class _NoCatalog:
		def install(self, tool_id: str) -> ToolInstallResult:
			return ToolInstallResult(tool_id=tool_id, ok=False, message="fail")

		def has_catalog_entry(self, tool_id: str) -> bool:
			return False

		def catalog_covers(self, tool_id: str) -> bool:
			return False

	service = ManagedToolsService(_NoCatalog(), dest_dir=tmp_path)
	# when
	payload = service.status_dict()
	# then
	assert "setup_hint" not in payload
	assert payload["show_iphone_usb_hint"] is False
	assert payload["summary_status"] == "missing"
	assert payload["package_manager_command"] is None
	bulk = payload["install_all_command"]
	assert isinstance(bulk, str)
	assert bulk.startswith("brew install")
	assert "ffmpeg" in bulk
	assert "imagemagick" in bulk
	assert "ifuse" not in bulk
	assert "libimobiledevice" not in bulk
	tools = payload["tools"]
	assert isinstance(tools, list)
	by_id = {str(row["tool_id"]): row for row in tools}
	assert "ifuse" not in by_id
	assert "idevice_id" not in by_id
	assert "idevicepair" not in by_id
	assert "ideviceinfo" not in by_id
	assert by_id["ffmpeg"]["install_command"] == "brew install ffmpeg"
	assert by_id["magick"]["install_command"] == "brew install imagemagick"
	assert by_id["exiftool"]["install_command"] == "brew install exiftool"
	assert by_id["adb"]["install_command"] == "brew install android-platform-tools"


def test_given_macos_when_ifuse_missing_then_no_brew_hint():
	# given
	tool_id = "ifuse"
	# when
	cmd = platform_setup_hints.install_command_for_tool(
		tool_id,
		phase="idle",
		resolution="missing",
		platform="darwin",
	)
	# then
	assert cmd is None


def test_given_windows_when_status_dict_then_omits_afc_tools(tmp_path: Path, monkeypatch):
	# given
	monkeypatch.setattr(sys, "platform", "win32")
	monkeypatch.setenv("SPACEMAKER_TOOLS_DIR", str(tmp_path))
	monkeypatch.setattr(platform_setup_hints.shutil, "which", lambda _name: None)
	monkeypatch.setattr("spacemaker.bootstrap.bundled_tools.shutil.which", lambda _name: None)
	monkeypatch.setattr("spacemaker.bootstrap.bundled_tools.host_tool_path_dirs", lambda: [])

	class _NoCatalog:
		def install(self, tool_id: str) -> ToolInstallResult:
			return ToolInstallResult(tool_id=tool_id, ok=False, message="fail")

		def has_catalog_entry(self, tool_id: str) -> bool:
			return False

		def catalog_covers(self, tool_id: str) -> bool:
			return False

	service = ManagedToolsService(_NoCatalog(), dest_dir=tmp_path)
	# when
	payload = service.status_dict()
	# then
	tools = payload["tools"]
	assert isinstance(tools, list)
	ids = {str(row["tool_id"]) for row in tools}
	assert "ifuse" not in ids
	assert "idevice_id" not in ids
	assert payload["show_iphone_usb_hint"] is False


def test_given_linux_when_status_dict_then_includes_ifuse(tmp_path: Path, monkeypatch):
	# given
	monkeypatch.setattr(sys, "platform", "linux")
	monkeypatch.setenv("SPACEMAKER_TOOLS_DIR", str(tmp_path))
	monkeypatch.setattr(
		"spacemaker.bootstrap.services.managed_tools.detect_linux_package_family",
		lambda **_kwargs: "apt",
	)
	monkeypatch.setattr(platform_setup_hints.shutil, "which", lambda _name: None)
	monkeypatch.setattr("spacemaker.bootstrap.bundled_tools.shutil.which", lambda _name: None)
	monkeypatch.setattr("spacemaker.bootstrap.bundled_tools.host_tool_path_dirs", lambda: [])

	class _NoCatalog:
		def install(self, tool_id: str) -> ToolInstallResult:
			return ToolInstallResult(tool_id=tool_id, ok=False, message="fail")

		def has_catalog_entry(self, tool_id: str) -> bool:
			return False

		def catalog_covers(self, tool_id: str) -> bool:
			return False

	service = ManagedToolsService(_NoCatalog(), dest_dir=tmp_path)
	# when
	payload = service.status_dict()
	# then
	tools = payload["tools"]
	assert isinstance(tools, list)
	by_id = {str(row["tool_id"]): row for row in tools}
	assert "ifuse" in by_id
	assert by_id["ifuse"]["resolution"] == "missing"
	assert by_id["ifuse"]["install_command"] == "sudo apt install ifuse"
	assert payload["show_iphone_usb_hint"] is True


def test_given_managed_adb_when_status_dict_then_omits_install_command(tmp_path: Path, monkeypatch):
	# given
	monkeypatch.setattr(sys, "platform", "darwin")
	monkeypatch.setenv("SPACEMAKER_TOOLS_DIR", str(tmp_path))
	adb = bundled_tool_path(BundledTool.ADB, root=tmp_path, platform_is_windows=False)
	adb.write_text("stub", encoding="utf-8")
	adb.chmod(0o755)

	class _NoCatalog:
		def install(self, tool_id: str) -> ToolInstallResult:
			return ToolInstallResult(tool_id=tool_id, ok=False)

		def has_catalog_entry(self, tool_id: str) -> bool:
			return False

		def catalog_covers(self, tool_id: str) -> bool:
			return False

	service = ManagedToolsService(_NoCatalog(), dest_dir=tmp_path)
	# when
	payload = service.status_dict()
	# then
	tools = payload["tools"]
	assert isinstance(tools, list)
	by_id = {str(row["tool_id"]): row for row in tools}
	assert by_id["adb"]["resolution"] == "managed"
	assert by_id["adb"]["install_command"] is None
