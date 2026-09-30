import sys
from pathlib import Path

from spacemaker.bootstrap.bundled_tools import BundledTool, bundled_tool_path
from spacemaker.bootstrap.services.managed_tools import ManagedToolsService
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


def test_given_path_ffmpeg_before_continue_when_snapshot_then_path_green_convert_gated(
	tmp_path: Path,
	monkeypatch,
):
	# given
	dest = tmp_path / "managed"
	dest.mkdir()
	monkeypatch.setenv("SPACEMAKER_TOOLS_DIR", str(dest))
	system_ffmpeg = tmp_path / "bin" / "ffmpeg"
	system_ffmpeg.parent.mkdir()
	system_ffmpeg.write_text("stub")
	system_ffmpeg.chmod(0o755)
	monkeypatch.setattr(
		"spacemaker.bootstrap.bundled_tools.shutil.which",
		lambda name: str(system_ffmpeg) if name == "ffmpeg" else None,
	)
	service = ManagedToolsService(FakeInstaller(entries=set()), dest_dir=dest)
	# when
	ffmpeg = next(item for item in service.snapshot() if item.tool_id == "ffmpeg")
	# then
	assert ffmpeg.resolution == ToolResolution.PATH
	assert service.permit_path_fallback(BundledTool.FFMPEG) is False
	assert service.setup_pending() is True


def test_given_path_only_tools_when_status_then_summary_ok_details_collapsed(tmp_path: Path, monkeypatch):
	# given — every BundledTool resolves via PATH
	dest = tmp_path / "managed"
	dest.mkdir()
	monkeypatch.setenv("SPACEMAKER_TOOLS_DIR", str(dest))
	bins = tmp_path / "bin"
	bins.mkdir()
	for tool in BundledTool:
		exe = bins / tool.value
		exe.write_text("stub")
		exe.chmod(0o755)
	monkeypatch.setattr(
		"spacemaker.bootstrap.bundled_tools.shutil.which",
		lambda name: str(bins / name) if (bins / name).is_file() else None,
	)
	service = ManagedToolsService(FakeInstaller(entries=set()), dest_dir=dest)
	# when
	payload = service.status_dict()
	# then
	assert payload["summary_status"] == "ok"
	assert payload["setup_pending"] is True
	assert payload["details_expanded"] is False
	assert payload["install_all_command"] is None


def test_given_all_managed_when_status_then_summary_ok_setup_not_pending(tmp_path: Path, monkeypatch):
	# given
	dest = tmp_path / "managed"
	dest.mkdir()
	monkeypatch.setenv("SPACEMAKER_TOOLS_DIR", str(dest))
	for tool in BundledTool:
		path = bundled_tool_path(tool, root=dest, platform_is_windows=False)
		path.write_text("stub")
		path.chmod(0o755)
	service = ManagedToolsService(FakeInstaller(entries=set()), dest_dir=dest)
	# when
	payload = service.status_dict()
	# then
	assert payload["summary_status"] == "ok"
	assert payload["setup_pending"] is False
	assert payload["details_expanded"] is False


def test_given_continue_when_called_then_ensures_host_path_dirs(tmp_path: Path, monkeypatch):
	# given
	dest = tmp_path / "managed"
	dest.mkdir()
	monkeypatch.setenv("SPACEMAKER_TOOLS_DIR", str(dest))
	called: list[bool] = []
	monkeypatch.setattr(
		"spacemaker.bootstrap.services.managed_tools.ensure_host_tool_path_dirs",
		lambda: called.append(True),
	)
	service = ManagedToolsService(FakeInstaller(entries=set()), dest_dir=dest)
	# when
	service.allow_path_fallback()
	# then
	assert called == [True]
	assert service.setup_pending() is False
