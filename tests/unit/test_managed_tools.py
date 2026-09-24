import sys
from pathlib import Path

from spacemaker.application.managed_tools import ManagedToolsService
from spacemaker.bootstrap.bundled_tools import BundledTool, bundled_tool_path
from spacemaker.domain.managed_tool import ToolResolution
from spacemaker.ports.outbound.tool_installer import ToolInstallResult


class FakeInstaller:
	def __init__(self, *, entries: set[str] | None = None, ok: bool = True) -> None:
		self.entries = entries or set()
		self.ok = ok
		self.installed: list[str] = []

	def has_catalog_entry(self, tool_id: str) -> bool:
		return tool_id in self.entries

	def catalog_covers(self, tool_id: str) -> bool:
		return tool_id in self.entries

	def install(self, tool_id: str) -> ToolInstallResult:
		self.installed.append(tool_id)
		return ToolInstallResult(tool_id=tool_id, ok=self.ok, message="" if self.ok else "fail")


def test_given_catalog_installs_when_ensure_then_places_file(tmp_path: Path, monkeypatch):
	dest = tmp_path / "managed"
	dest.mkdir()
	installer = FakeInstaller(entries={"adb"})
	service = ManagedToolsService(installer, dest_dir=dest)

	def fake_install(tool_id: str) -> ToolInstallResult:
		installer.installed.append(tool_id)
		is_windows = sys.platform == "win32"
		path = bundled_tool_path(BundledTool.ADB, root=dest, platform_is_windows=is_windows)
		path.write_text("stub")
		if not is_windows:
			path.chmod(0o755)
		return ToolInstallResult(tool_id=tool_id, ok=True)

	installer.install = fake_install  # type: ignore[method-assign]
	monkeypatch.setenv("SPACEMAKER_TOOLS_DIR", str(dest))

	service.ensure_all()
	snapshot = service.snapshot()
	adb = next(item for item in snapshot if item.tool_id == "adb")
	assert adb.resolution == ToolResolution.MANAGED


def test_given_delete_when_called_then_clears_managed_dir(tmp_path: Path):
	dest = tmp_path / "managed"
	dest.mkdir()
	tool = bundled_tool_path(BundledTool.FFMPEG, root=dest, platform_is_windows=False)
	tool.write_text("x")
	service = ManagedToolsService(FakeInstaller(), dest_dir=dest)
	service.delete_downloaded()
	assert not tool.exists()
	assert dest.is_dir()


def test_given_empty_managed_and_catalog_entry_when_downloads_pending_then_true(
	tmp_path: Path,
	monkeypatch,
):
	dest = tmp_path / "managed"
	dest.mkdir()
	monkeypatch.setenv("SPACEMAKER_TOOLS_DIR", str(dest))
	system_ffmpeg = tmp_path / "system-ffmpeg"
	system_ffmpeg.write_text("stub")
	system_ffmpeg.chmod(0o755)
	monkeypatch.setattr(
		"spacemaker.bootstrap.bundled_tools.shutil.which",
		lambda name: str(system_ffmpeg) if name == "ffmpeg" else None,
	)
	service = ManagedToolsService(FakeInstaller(entries={"ffmpeg"}), dest_dir=dest)
	assert service.downloads_pending() is True
	assert service.setup_pending() is True
	assert service.permit_path_fallback(BundledTool.FFMPEG) is False


def test_given_download_failed_when_permit_path_then_false_until_continue(tmp_path: Path, monkeypatch):
	dest = tmp_path / "managed"
	dest.mkdir()
	monkeypatch.setenv("SPACEMAKER_TOOLS_DIR", str(dest))
	installer = FakeInstaller(entries={"adb"}, ok=False)
	service = ManagedToolsService(installer, dest_dir=dest)
	service.ensure_all()
	assert service.permit_path_fallback(BundledTool.ADB) is False
	service.allow_path_fallback()
	assert service.permit_path_fallback(BundledTool.ADB) is True
	assert service.setup_pending() is False


def test_given_continue_marker_on_disk_when_new_service_then_setup_not_pending(tmp_path: Path, monkeypatch):
	dest = tmp_path / "managed"
	dest.mkdir()
	monkeypatch.setenv("SPACEMAKER_TOOLS_DIR", str(dest))
	installer = FakeInstaller(entries={"adb"}, ok=False)
	first = ManagedToolsService(installer, dest_dir=dest)
	first.allow_path_fallback()
	second = ManagedToolsService(installer, dest_dir=dest)
	assert second.setup_pending() is False
