from __future__ import annotations

import contextlib
import os
import threading
from collections.abc import Callable
from pathlib import Path


_ENTRY_SUFFIX = ".jpg"


class FileDevicePreviewCache:
	"""``DevicePreviewCachePort`` on disk: one ``<key>.jpg`` per entry, LRU by file mtime.

	Recency is stamped from the injected ``now`` (``os.utime``) on put and on every get hit; writes are
	temp file + rename so a reader never sees a partial entry; ``*.tmp`` files are never served or counted.
	"""

	def __init__(self, root: Path, max_bytes: int, now: Callable[[], float]) -> None:
		self._root = Path(root)
		self._max_bytes = max_bytes
		self._now = now
		self._lock = threading.Lock()

	def _entry_path(self, key: str) -> Path:
		return self._root / f"{key}{_ENTRY_SUFFIX}"

	def get(self, key: str) -> bytes | None:
		path = self._entry_path(key)
		with self._lock:
			try:
				data = path.read_bytes()
			except OSError:
				return None
			stamp = self._now()
			with contextlib.suppress(OSError):
				os.utime(path, (stamp, stamp))
			return data

	def put(self, key: str, jpeg: bytes) -> None:
		path = self._entry_path(key)
		with self._lock:
			try:
				self._root.mkdir(parents=True, exist_ok=True)
				temp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
				try:
					temp.write_bytes(jpeg)
					stamp = self._now()
					os.utime(temp, (stamp, stamp))
					os.replace(temp, path)
				finally:
					temp.unlink(missing_ok=True)
			except OSError:
				return
			self._evict(keep=path)

	def _evict(self, keep: Path) -> None:
		entries: list[tuple[float, int, Path]] = []
		total = 0
		with contextlib.suppress(OSError):
			for item in self._root.iterdir():
				if item.suffix != _ENTRY_SUFFIX:
					continue
				try:
					info = item.stat()
				except OSError:
					continue
				total += info.st_size
				if item != keep:
					entries.append((info.st_mtime, info.st_size, item))
		entries.sort(key=lambda entry: entry[0])
		for _mtime, size, item in entries:
			if total <= self._max_bytes:
				break
			with contextlib.suppress(OSError):
				item.unlink()
				total -= size
