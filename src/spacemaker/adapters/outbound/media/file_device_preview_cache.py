from __future__ import annotations

import contextlib
import os
import threading
from collections.abc import Callable
from pathlib import Path

from spacemaker.domain.device_preview import CachedDevicePreview


_ENTRY_SUFFIX = ".jpg"
_DURATION_SUFFIX = ".dur"


class FileDevicePreviewCache:
	"""``DevicePreviewCachePort`` on disk: one ``<key>.jpg`` per entry, LRU by file mtime.

	Recency is stamped from the injected ``now`` (``os.utime``) on put and on every get hit; writes are
	temp file + rename so a reader never sees a partial entry; ``*.tmp`` files are never served or counted.

	A video's duration lives in a sidecar ``<key>.dur`` (decimal seconds, text) renamed in before the JPEG, so a
	``.jpg`` never appears without its duration; if a put fails the sidecar is removed again, and orphan
	sidecars found while evicting are deleted. Photos have no sidecar. Sidecar bytes
	count toward the size limit and are evicted together with their JPEG.
	"""

	def __init__(self, root: Path, max_bytes: int, now: Callable[[], float]) -> None:
		self._root = Path(root)
		self._max_bytes = max_bytes
		self._now = now
		self._lock = threading.Lock()

	def _entry_path(self, key: str) -> Path:
		return self._root / f"{key}{_ENTRY_SUFFIX}"

	def _duration_path(self, key: str) -> Path:
		return self._root / f"{key}{_DURATION_SUFFIX}"

	def get(self, key: str) -> CachedDevicePreview | None:
		path = self._entry_path(key)
		with self._lock:
			try:
				data = path.read_bytes()
			except OSError:
				return None
			stamp = self._now()
			with contextlib.suppress(OSError):
				os.utime(path, (stamp, stamp))
			duration: float | None = None
			with contextlib.suppress(OSError, ValueError):
				duration = float(self._duration_path(key).read_text())
			return CachedDevicePreview(data, duration)

	def put(self, key: str, entry: CachedDevicePreview) -> None:
		path = self._entry_path(key)
		sidecar = self._duration_path(key)
		with self._lock:
			suffix = f".{os.getpid()}.{threading.get_ident()}.tmp"
			temp = path.with_name(path.name + suffix)
			sidecar_temp = sidecar.with_name(sidecar.name + suffix)
			try:
				self._root.mkdir(parents=True, exist_ok=True)
				temp.write_bytes(entry.jpeg)
				stamp = self._now()
				os.utime(temp, (stamp, stamp))
				if entry.duration_s is None:
					sidecar.unlink(missing_ok=True)
				else:
					sidecar_temp.write_text(repr(entry.duration_s))
					os.replace(sidecar_temp, sidecar)
				os.replace(temp, path)
			except OSError:
				with contextlib.suppress(OSError):
					sidecar.unlink(missing_ok=True)  # never leave a duration without its JPEG
				return
			finally:
				temp.unlink(missing_ok=True)
				sidecar_temp.unlink(missing_ok=True)
			self._evict(keep=path)

	def _evict(self, keep: Path) -> None:
		entries: list[tuple[float, int, Path]] = []
		total = 0
		with contextlib.suppress(OSError):
			for item in self._root.iterdir():
				if item.suffix == _DURATION_SUFFIX and not item.with_suffix(_ENTRY_SUFFIX).exists():
					with contextlib.suppress(OSError):
						item.unlink()  # orphan sidecar (its JPEG is gone): reclaim it
					continue
				if item.suffix != _ENTRY_SUFFIX:
					continue
				try:
					info = item.stat()
				except OSError:
					continue
				size = info.st_size
				with contextlib.suppress(OSError):
					size += item.with_suffix(_DURATION_SUFFIX).stat().st_size
				total += size
				if item != keep:
					entries.append((info.st_mtime, size, item))
		entries.sort(key=lambda entry: entry[0])
		for _mtime, size, item in entries:
			if total <= self._max_bytes:
				break
			with contextlib.suppress(OSError):
				item.unlink()
				total -= size
			with contextlib.suppress(OSError):
				item.with_suffix(_DURATION_SUFFIX).unlink()
