import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from spacemaker.adapters.inbound.web.app import create_fastapi_app
from spacemaker.adapters.inbound.web.session import AppSession
from spacemaker.adapters.outbound.filesystem.local import LocalFileSystem
from spacemaker.adapters.outbound.media.subprocess_thumbnails import SubprocessThumbnailGenerator
from spacemaker.adapters.outbound.media.tool_runner import ToolExecutionError, ToolRunner
from spacemaker.bootstrap.bundled_tools import BundledTool
from spacemaker.bootstrap.services import AppServices
from spacemaker.bootstrap.ui_shell import THUMB_CACHE_HEADERS
from spacemaker.domain.library import LibraryFolder


class _StubToolRunner(ToolRunner):
	"""Records invocations and either writes the requested destination or fails, without spawning a subprocess."""

	def __init__(self, *, fail: bool = False) -> None:
		self._fail = fail

	def run(self, tool: BundledTool, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
		if self._fail:
			result = subprocess.CompletedProcess(args, returncode=1, stdout="", stderr="boom")
			if check:
				raise ToolExecutionError(tool, args, result)
			return result
		Path(args[-1]).write_bytes(b"thumb")
		return subprocess.CompletedProcess(args, returncode=0, stdout="", stderr="")


class _StubServices(AppServices):
	"""Minimal AppServices for testing the /thumbs route without wiring the real composition root."""

	def __init__(self, library_root: str, thumbnails: SubprocessThumbnailGenerator) -> None:
		self.session = AppSession(library_root=library_root)
		self.filesystem = LocalFileSystem()
		self.thumbnails = thumbnails

	def shutdown(self, *, timeout_seconds: float = 10.0) -> None:
		pass


def _install_processed_file(library: Path, rel: str) -> Path:
	target = library / LibraryFolder.PROCESSED.value / rel
	target.parent.mkdir(parents=True, exist_ok=True)
	target.write_bytes(b"avif-bytes")
	return target


def test_given_thumbnail_generation_fails_when_get_thumb_then_returns_503_without_cache_headers(
	tmp_path: Path,
) -> None:
	# given
	library = tmp_path / "lib"
	rel = "photo.avif"
	_install_processed_file(library, rel)
	thumbnails = SubprocessThumbnailGenerator(_StubToolRunner(fail=True))
	services = _StubServices(str(library), thumbnails)
	client = TestClient(create_fastapi_app(services))
	# when
	response = client.get(f"/thumbs/{rel}")
	# then
	assert response.status_code == 503
	for key in THUMB_CACHE_HEADERS:
		assert key not in response.headers


def test_given_thumbnail_generation_succeeds_when_get_thumb_then_returns_cached_jpeg(tmp_path: Path) -> None:
	# given
	library = tmp_path / "lib"
	rel = "photo.avif"
	_install_processed_file(library, rel)
	thumbnails = SubprocessThumbnailGenerator(_StubToolRunner())
	services = _StubServices(str(library), thumbnails)
	client = TestClient(create_fastapi_app(services))
	# when
	response = client.get(f"/thumbs/{rel}")
	# then
	assert response.status_code == 200
	for key, value in THUMB_CACHE_HEADERS.items():
		assert response.headers[key] == value
	assert response.headers["etag"]


def test_given_matching_if_none_match_when_get_thumb_then_returns_304_without_body(tmp_path: Path) -> None:
	# given
	library = tmp_path / "lib"
	rel = "photo.avif"
	_install_processed_file(library, rel)
	thumbnails = SubprocessThumbnailGenerator(_StubToolRunner())
	services = _StubServices(str(library), thumbnails)
	client = TestClient(create_fastapi_app(services))
	first = client.get(f"/thumbs/{rel}")
	etag = first.headers["etag"]
	# when
	response = client.get(f"/thumbs/{rel}", headers={"If-None-Match": etag})
	# then
	assert response.status_code == 304
	assert response.content == b""
	assert response.headers["etag"] == etag


def test_given_stale_if_none_match_when_get_thumb_then_returns_200_with_body(tmp_path: Path) -> None:
	# given
	library = tmp_path / "lib"
	rel = "photo.avif"
	_install_processed_file(library, rel)
	thumbnails = SubprocessThumbnailGenerator(_StubToolRunner())
	services = _StubServices(str(library), thumbnails)
	client = TestClient(create_fastapi_app(services))
	# when
	response = client.get(f"/thumbs/{rel}", headers={"If-None-Match": '"not-the-real-etag"'})
	# then
	assert response.status_code == 200
	assert response.content == b"thumb"


def test_given_no_processed_file_when_get_thumb_then_returns_404(tmp_path: Path) -> None:
	# given
	library = tmp_path / "lib"
	thumbnails = SubprocessThumbnailGenerator(_StubToolRunner())
	services = _StubServices(str(library), thumbnails)
	client = TestClient(create_fastapi_app(services))
	# when
	response = client.get("/thumbs/missing.avif")
	# then
	assert response.status_code == 404
