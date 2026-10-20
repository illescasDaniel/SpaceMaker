from __future__ import annotations

import re
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


def android_stat_file_command(path: str) -> str:
	"""Shell command printing one ``%F|%s|%Y|%n`` record for one file under user storage (``path`` validated)."""
	return f"stat -L -c {shlex.quote(_STAT_FORMAT)} {shlex.quote(f'{_STORAGE_ROOT}/{path}')}"


_HEADER = re.compile(r"^([A-Za-z][A-Za-z ]*)\|(\d+)\|(-?\d+)\|(.*)$")


def parse_android_stat_listing(output: str) -> list[DeviceEntry]:
	"""Parse ``%F|%s|%Y|%n`` records; a line that is not a record header continues the previous name (newline in a name)."""
	records: list[list[str]] = []
	for line in output.removesuffix("\n").split("\n"):
		match = _HEADER.match(line)
		if match:
			records.append(list(match.groups()))
		elif records and not line.startswith(("stat:", "find:")):
			records[-1][3] += "\n" + line
	entries: list[DeviceEntry] = []
	for kind, size_text, mtime_text, raw_name in records:
		name = raw_name.removeprefix("./")
		if not name.strip("\n"):
			continue
		entries.append(
			DeviceEntry(name=name, is_dir=kind.strip() == "directory", size=int(size_text), mtime=int(mtime_text))
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
