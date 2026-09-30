import io
import json
import zipfile
from pathlib import Path

from spacemaker.adapters.outbound.tools.catalog_installer import CatalogToolInstaller


_REPO = Path(__file__).resolve().parents[2]


def test_given_win_catalog_when_avifenc_entry_then_points_at_libavif_release():
	catalog = json.loads((_REPO / "packaging" / "tool-catalog.json").read_text(encoding="utf-8"))
	entry = catalog["platforms"]["win-x86_64"]["avifenc"]
	assert entry["strategy"] == "zip"
	assert "libavif/releases/download/v1.4.2/windows-artifacts.zip" in entry["url"]
	assert entry["files"]["avifenc"] == "avifenc.exe"


def test_given_zip_when_install_avifenc_then_places_binary(tmp_path: Path):
	buf = io.BytesIO()
	with zipfile.ZipFile(buf, "w") as archive:
		archive.writestr("avifenc.exe", b"stub-avifenc")
		archive.writestr("avifdec.exe", b"stub-avifdec")
	installer = CatalogToolInstaller(
		repo_root=_REPO,
		dest_dir=tmp_path,
		platform_key="win-x86_64",
		platform_is_windows=True,
	)

	def fake_download(_url: str) -> bytes:
		return buf.getvalue()

	installer._download_bytes = fake_download  # type: ignore[method-assign]
	result = installer.install("avifenc")
	assert result.ok is True
	assert (tmp_path / "avifenc.exe").read_bytes() == b"stub-avifenc"


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
