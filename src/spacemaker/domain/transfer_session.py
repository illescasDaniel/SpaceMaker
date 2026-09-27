from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath


class TransferItemKind(StrEnum):
	FILE = "file"
	FOLDER_ZIP = "folder_zip"


class TransferOrigin(StrEnum):
	PC = "pc"
	PHONE = "phone"


class TransferIngestDisposition(StrEnum):
	ADDED = "added"
	SKIPPED_DUPLICATE = "skipped_duplicate"


@dataclass(frozen=True, slots=True)
class TransferSessionItem:
	file_id: str
	display_name: str
	staged_path: str
	content_hash: str
	kind: TransferItemKind
	origin: TransferOrigin


@dataclass(frozen=True, slots=True)
class TransferNameAllocation:
	disposition: TransferIngestDisposition
	display_name: str


def folder_zip_display_name(folder_name: str) -> str:
	"""Display name for a folder staged as a single zip row."""
	base = PurePosixPath(folder_name.replace("\\", "/")).name.strip()
	if not base:
		raise ValueError("invalid folder name")
	if base.lower().endswith(".zip"):
		return base
	return f"{base}.zip"


def split_filename_stem_suffix(name: str) -> tuple[str, str]:
	"""Split before the final extension: report.pdf → (report, .pdf)."""
	pure = PurePosixPath(name)
	if pure.suffix:
		return pure.stem, pure.suffix
	return name, ""


def next_suffixed_display_name(requested_name: str, taken: set[str]) -> str:
	"""Return requested_name if free; otherwise name (2).ext, name (3).ext, …"""
	if requested_name not in taken:
		return requested_name
	stem, suffix = split_filename_stem_suffix(requested_name)
	n = 2
	while True:
		candidate = f"{stem} ({n}){suffix}"
		if candidate not in taken:
			return candidate
		n += 1


def allocate_transfer_display_name(
	requested_name: str,
	content_hash: str,
	existing: list[TransferSessionItem],
) -> TransferNameAllocation:
	"""Resolve collisions: same name+hash → skip; same name+different hash → suffix."""
	clean = requested_name.strip()
	if not clean or "/" in clean.replace("\\", "/") or clean in {".", ".."}:
		raise ValueError("invalid display name")
	for item in existing:
		if item.display_name == clean and item.content_hash == content_hash:
			return TransferNameAllocation(TransferIngestDisposition.SKIPPED_DUPLICATE, clean)
	taken = {item.display_name for item in existing}
	return TransferNameAllocation(
		TransferIngestDisposition.ADDED,
		next_suffixed_display_name(clean, taken),
	)
