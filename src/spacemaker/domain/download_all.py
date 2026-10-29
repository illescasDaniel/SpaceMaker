from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from spacemaker.domain.transfer_session import next_suffixed_display_name


_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")
_FALLBACK_ENTRY_NAME = "file"


class DownloadAllKind(StrEnum):
	SHARE = "share"
	TRANSFER = "transfer"

	@property
	def zip_filename(self) -> str:
		"""Download name of the archive: ``SpaceMaker-share.zip`` / ``SpaceMaker-transfer.zip``."""
		return f"SpaceMaker-{self.value}.zip"


@dataclass(frozen=True, slots=True)
class DownloadAllItem:
	"""One manifest row; folder rows are expanded to their files by the use case."""

	name: str
	source_path: str
	is_folder: bool


class NothingToDownloadError(Exception):
	"""No file is left to archive (F2)."""


class DownloadAllBuildError(Exception):
	"""The archive could not be built (F4)."""


def sanitize_entry_name(raw: str) -> str:
	"""Return a safe zip entry name for ``raw``.

	Contract: a name containing a ``..`` segment is reduced to its last segment; uses ``/`` separators, contains no ``..`` segment, is not absolute and has no drive
	letter, and is never empty (a fallback name is used when nothing usable remains).
	"""
	parts = raw.replace("\\", "/").split("/")
	if parts:
		parts[0] = _DRIVE_PREFIX.sub("", parts[0])
	kept = [part.strip() for part in parts if part.strip() not in {"", ".", ".."}]
	if ".." in (part.strip() for part in parts):
		kept = kept[-1:]  # traversal attempt: only the leaf survives
	return "/".join(kept) or _FALLBACK_ENTRY_NAME


def dedupe_entry_names(names: Sequence[str]) -> list[str]:
	"""Return ``names`` made unique, in order: the second ``report.pdf`` becomes ``report (2).pdf``.

	Delegates to ``next_suffixed_display_name``; the result has the same length as ``names``.
	"""
	taken: set[str] = set()
	result: list[str] = []
	for name in names:
		unique = next_suffixed_display_name(name, taken)
		taken.add(unique)
		result.append(unique)
	return result
