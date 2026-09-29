from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import cast


class JsonUserPreferences:
	"""Disk-backed preferences JSON under the SpaceMaker data directory."""

	def __init__(self, path: Path) -> None:
		self._path = path
		self._lock = threading.Lock()

	def get_compress_media(self) -> bool | None:
		data = self._read()
		value = data.get("compress_media")
		if isinstance(value, bool):
			return value
		return None

	def set_compress_media(self, enabled: bool) -> None:
		with self._lock:
			data = self._read_unlocked()
			data["compress_media"] = bool(enabled)
			self._write_unlocked(data)

	def clear(self) -> None:
		with self._lock:
			self._path.parent.mkdir(parents=True, exist_ok=True)
			if self._path.is_file():
				self._path.unlink()
			# Remove any leftover temp from a crashed write.
			tmp = self._path.with_suffix(self._path.suffix + ".tmp")
			tmp.unlink(missing_ok=True)

	def _read(self) -> dict[str, object]:
		with self._lock:
			return self._read_unlocked()

	def _read_unlocked(self) -> dict[str, object]:
		if not self._path.is_file():
			return {}
		try:
			raw = json.loads(self._path.read_text(encoding="utf-8"))
		except (OSError, json.JSONDecodeError, UnicodeDecodeError):
			return {}
		if not isinstance(raw, dict):
			return {}
		# Preserve unknown keys so future preferences / migrations stay intact.
		return cast(dict[str, object], raw)

	def _write_unlocked(self, data: dict[str, object]) -> None:
		self._path.parent.mkdir(parents=True, exist_ok=True)
		text = json.dumps(data, indent="\t", sort_keys=True) + "\n"
		tmp = self._path.with_suffix(self._path.suffix + ".tmp")
		tmp.write_text(text, encoding="utf-8")
		tmp.replace(self._path)
