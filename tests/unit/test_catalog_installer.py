import io
import json
import zipfile
from pathlib import Path

from spacemaker.adapters.outbound.tools.catalog_installer import CatalogToolInstaller


_REPO = Path(__file__).resolve().parents[2]


def test_given_win_catalog_when_ffmpeg_entry_then_uses_release_redirect_url():
	catalog = json.loads((_REPO / "packaging" / "tool-catalog.json").read_text(encoding="utf-8"))
	entry = catalog["platforms"]["win-x86_64"]["ffmpeg"]
	assert "ffmpeg-release-essentials" in entry["url"]
	assert "7.1.1-essentials_build" not in entry["url"]


def test_given_zip_flatten_when_install_then_places_exiftool_tree(tmp_path: Path):
	buf = io.BytesIO()
	with zipfile.ZipFile(buf, "w") as archive:
		archive.writestr("exiftool-13.59_64/exiftool(-k).exe", b"stub-exe")
		archive.writestr("exiftool-13.59_64/exiftool_files/readme.txt", b"support")
	installer = CatalogToolInstaller(
		repo_root=_REPO,
		dest_dir=tmp_path,
		platform_key="win-x86_64",
		platform_is_windows=True,
	)

	def fake_download(_url: str) -> bytes:
		return buf.getvalue()

	installer._download_bytes = fake_download  # type: ignore[method-assign]
	result = installer.install("exiftool")
	assert result.ok is True
	assert (tmp_path / "exiftool.exe").is_file()
	assert (tmp_path / "exiftool_files" / "readme.txt").is_file()


def test_given_failed_ffmpeg_on_windows_when_hint_then_includes_gyan_winget(monkeypatch):
	from spacemaker.bootstrap import platform_setup_hints

	monkeypatch.setattr(platform_setup_hints.sys, "platform", "win32")
	hint = platform_setup_hints.components_setup_hint(
		tools=[
			{"tool_id": "ffmpeg", "phase": "failed", "resolution": "missing"},
			{"tool_id": "magick", "phase": "idle", "resolution": "missing"},
		],
	)
	assert hint is not None
	assert "Gyan.FFmpeg" in hint["command"]
	assert "ImageMagick.ImageMagick" in hint["command"]


def test_given_managed_ffmpeg_when_hint_then_omits_gyan(monkeypatch):
	from spacemaker.bootstrap import platform_setup_hints

	monkeypatch.setattr(platform_setup_hints.sys, "platform", "win32")
	hint = platform_setup_hints.components_setup_hint(
		tools=[
			{"tool_id": "ffmpeg", "phase": "ready", "resolution": "managed"},
			{"tool_id": "magick", "phase": "idle", "resolution": "missing"},
		],
	)
	assert hint is not None
	assert "Gyan.FFmpeg" not in hint["command"]
	assert "ImageMagick.ImageMagick" in hint["command"]
