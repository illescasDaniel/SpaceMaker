import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from spacemaker.adapters.inbound.desktop_download import DownloadRegistry, is_allowed_download_url


@pytest.mark.parametrize(
	"url",
	[
		"http://127.0.0.1:8765/api/gallery/batch/convert/abc/file",
		"http://localhost:8765/api/gallery/batch/convert/abc/file",
		"http://127.0.0.1:8765/media/2025/a.avif?download=1",
		"http://127.0.0.1:8765/api/gallery/export/abc/file",
	],
)
def test_given_loopback_batch_file_url_when_checked_then_allowed(url: str) -> None:
	# given
	# when
	allowed = is_allowed_download_url(url)
	# then
	assert allowed is True


@pytest.mark.parametrize(
	"url",
	[
		"http://example.com/api/gallery/batch/convert/abc/file",
		"http://127.0.0.1:8765/api/library/settings",
		"file:///etc/passwd",
		"http://127.0.0.1:8765/media/2025/a.avif",
		"http://192.168.1.5:8765/api/gallery/batch/convert/abc/file",
	],
)
def test_given_foreign_host_or_other_path_when_checked_then_refused(url: str) -> None:
	# given
	# when
	allowed = is_allowed_download_url(url)
	# then
	assert allowed is False


def test_given_served_file_when_registry_downloads_then_file_written_with_full_progress(tmp_path: Path) -> None:
	# given
	payload = b"zip-bytes" * 1000

	class Handler(BaseHTTPRequestHandler):
		def do_GET(self) -> None:  # noqa: N802
			self.send_response(200)
			self.send_header("Content-Length", str(len(payload)))
			self.end_headers()
			self.wfile.write(payload)

		def log_message(self, format: str, *args: object) -> None:  # noqa: A002
			return

	server = HTTPServer(("127.0.0.1", 0), Handler)
	threading.Thread(target=server.serve_forever, daemon=True).start()
	destination = tmp_path / "out.zip"
	registry = DownloadRegistry()
	# when
	download_id = registry.start(f"http://127.0.0.1:{server.server_port}/x", str(destination))
	deadline = time.time() + 5
	while not registry.progress(download_id)["done"] and time.time() < deadline:
		time.sleep(0.02)
	server.shutdown()
	# then
	progress = registry.progress(download_id)
	assert progress["error"] == ""
	assert progress["percent"] == 100
	assert destination.read_bytes() == payload
