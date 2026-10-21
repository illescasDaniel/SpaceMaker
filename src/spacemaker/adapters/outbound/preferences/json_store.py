from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import cast

from spacemaker.domain.device_browse import DeviceBrowseSort, parse_device_browse_sort
from spacemaker.domain.device_view import (
	DeviceViewMemory,
	DeviceViewSetting,
	dump_device_view_memory,
	parse_device_view_memory,
	remember_view,
)


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

	def get_usb_transfer_destination(self) -> str | None:
		value = self._read().get("usb_transfer_destination")
		if isinstance(value, str) and value.strip():
			return value
		return None

	def set_usb_transfer_destination(self, path: str | None) -> None:
		with self._lock:
			data = self._read_unlocked()
			if path and path.strip():
				data["usb_transfer_destination"] = path
			else:
				data.pop("usb_transfer_destination", None)
			self._write_unlocked(data)

	def get_device_picker_sort(self) -> DeviceBrowseSort | None:
		value = self._read().get("device_picker_sort")
		if not isinstance(value, dict):
			return None
		return parse_device_browse_sort(value.get("sort"), value.get("order"))

	def set_device_picker_sort(self, sort: DeviceBrowseSort | None) -> None:
		with self._lock:
			data = self._read_unlocked()
			if sort is None:
				data.pop("device_picker_sort", None)
			else:
				data["device_picker_sort"] = {"sort": sort.key.value, "order": sort.order.value}
			self._write_unlocked(data)

	def get_device_picker_views(self) -> DeviceViewMemory:
		return parse_device_view_memory(self._read().get("device_picker_views"))

	def set_device_picker_view(self, path: str, setting: DeviceViewSetting) -> None:
		with self._lock:
			data = self._read_unlocked()
			memory = remember_view(parse_device_view_memory(data.get("device_picker_views")), path, setting)
			if memory:
				data["device_picker_views"] = dump_device_view_memory(memory)
			else:
				data.pop("device_picker_views", None)
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
		# No sort_keys: the order of device_picker_views keys is the LRU order.
		text = json.dumps(data, indent="\t") + "\n"
		tmp = self._path.with_suffix(self._path.suffix + ".tmp")
		tmp.write_text(text, encoding="utf-8")
		tmp.replace(self._path)
