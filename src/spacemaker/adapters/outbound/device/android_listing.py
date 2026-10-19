from __future__ import annotations

import shlex

from spacemaker.domain.device_browse import DeviceBrowseErrorKind, DeviceEntry


_STORAGE_ROOT = "/sdcard"
_STAT_FORMAT = "%F|%s|%Y|%n"


def android_list_command(path: str) -> str:
	"""Shell command listing one directory under user storage (no recursion).

	``path`` must already be validated (storage-relative, no ``..``). The whole
	directory is passed as a single quoted argument; names come back from ``stat``.
	"""
	target = f"{_STORAGE_ROOT}/{path}" if path else _STORAGE_ROOT
	return (
		f"cd {shlex.quote(target)} && "
		f"find . -maxdepth 1 -mindepth 1 -exec stat -L -c {shlex.quote(_STAT_FORMAT)} {{}} +"
	)


def parse_android_stat_listing(output: str) -> list[DeviceEntry]:
	"""Parse ``%F|%s|%Y|%n`` lines; skip blanks and error lines (the name is last, so ``|`` in names is safe)."""
	entries: list[DeviceEntry] = []
	for line in output.splitlines():
		parts = line.split("|", 3)
		if len(parts) != 4:
			continue
		kind, size_text, mtime_text, name = parts
		if not size_text.strip().isdigit() or not mtime_text.strip().lstrip("-").isdigit():
			continue
		name = name.removeprefix("./")
		if not name:
			continue
		entries.append(
			DeviceEntry(
				name=name,
				is_dir=kind.strip() == "directory",
				size=int(size_text),
				mtime=int(mtime_text),
			),
		)
	return entries


def classify_android_shell_failure(text: str) -> DeviceBrowseErrorKind:
	lower = text.lower()
	if "permission denied" in lower:
		return DeviceBrowseErrorKind.PERMISSION_DENIED
	if "unauthorized" in lower:
		return DeviceBrowseErrorKind.UNAUTHORIZED
	if "offline" in lower or ("device" in lower and "not found" in lower) or "no devices" in lower:
		return DeviceBrowseErrorKind.UNPLUGGED
	if "no such file" in lower or "not a directory" in lower:
		return DeviceBrowseErrorKind.NOT_FOUND
	return DeviceBrowseErrorKind.FAILED
