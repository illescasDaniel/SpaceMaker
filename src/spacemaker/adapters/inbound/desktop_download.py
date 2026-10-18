from __future__ import annotations

import threading
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


# Only the finished batch zip may be saved through the desktop bridge.
_ALLOWED_PATH_PREFIX = "/api/gallery/batch/convert/"
_EXPORT_PATH_PREFIX = "/api/gallery/export/"
_MEDIA_PATH_PREFIX = "/media/"
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "[::1]"})
_CHUNK = 1024 * 256


@dataclass(slots=True)
class DownloadState:
	downloaded: int = 0
	total: int = 0
	done: bool = False
	error: str = ""
	path: str = ""

	def to_dict(self) -> dict[str, object]:
		percent = int(self.downloaded * 100 / self.total) if self.total else (100 if self.done else 0)
		return {
			"downloaded": self.downloaded,
			"total": self.total,
			"percent": min(100, percent),
			"done": self.done,
			"error": self.error,
			"path": self.path,
		}


def is_allowed_download_url(url: str) -> bool:
	"""Only the batch-convert file URL on this machine; anything else is refused."""
	parts = urlsplit(url)
	host = parts.hostname or ""
	if parts.scheme != "http" or (host if host != "::1" else "[::1]") not in _LOOPBACK_HOSTS:
		return False
	if parts.path.startswith((_ALLOWED_PATH_PREFIX, _EXPORT_PATH_PREFIX)) and parts.path.endswith("/file"):
		return True
	# The stored file of a gallery item, as served for the item page **Download**.
	return parts.path.startswith(_MEDIA_PATH_PREFIX) and "download=1" in parts.query.split("&")


class DownloadRegistry:
	"""Streams an allowed loopback URL to a user-chosen path in a thread, with pollable progress."""

	def __init__(self) -> None:
		self._states: dict[str, DownloadState] = {}
		self._lock = threading.Lock()

	def start(self, url: str, destination: str) -> str:
		download_id = uuid.uuid4().hex
		state = DownloadState(path=destination)
		with self._lock:
			self._states[download_id] = state
		threading.Thread(target=self._run, args=(url, destination, state), daemon=True).start()
		return download_id

	def progress(self, download_id: str) -> dict[str, object]:
		with self._lock:
			state = self._states.get(download_id)
		if state is None:
			return {"downloaded": 0, "total": 0, "percent": 0, "done": True, "error": "unknown download", "path": ""}
		return state.to_dict()

	@staticmethod
	def _run(url: str, destination: str, state: DownloadState) -> None:
		target = Path(destination)
		partial = target.with_name(target.name + ".part")
		try:
			with urllib.request.urlopen(url, timeout=30) as response, partial.open("wb") as handle:  # noqa: S310 - url validated
				state.total = int(response.headers.get("Content-Length") or 0)
				while chunk := response.read(_CHUNK):
					handle.write(chunk)
					state.downloaded += len(chunk)
			partial.replace(target)
			state.done = True
		except Exception as exc:  # noqa: BLE001 - surfaced to the UI
			state.error = str(exc) or "download failed"
			state.done = True
			partial.unlink(missing_ok=True)
