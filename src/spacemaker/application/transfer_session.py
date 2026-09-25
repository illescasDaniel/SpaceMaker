from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from spacemaker.application.file_share_manifest import count_shareable_files_in_root, write_folder_zip
from spacemaker.domain.transfer_session import (
	TransferIngestDisposition,
	TransferItemKind,
	TransferOrigin,
	TransferSessionItem,
	allocate_transfer_display_name,
	folder_zip_display_name,
)
from spacemaker.ports.outbound.content_hasher import ContentHasher
from spacemaker.ports.outbound.filesystem import FileSystemPort


class EmptyTransferFolderError(ValueError):
	"""User selected a folder with zero files."""


EMPTY_TRANSFER_FOLDER_MESSAGE = (
	"This folder has no files. Choose a folder that contains at least one file."
)


@dataclass(frozen=True, slots=True)
class TransferStageOutcome:
	disposition: TransferIngestDisposition
	item: TransferSessionItem | None


class StageTransferItem:
	"""Copy an uploaded or PC-added file into ephemeral transfer staging."""

	def __init__(self, filesystem: FileSystemPort, hasher: ContentHasher) -> None:
		self._filesystem = filesystem
		self._hasher = hasher

	def stage_file(
		self,
		staging_root: str,
		*,
		file_id: str,
		requested_name: str,
		temp_path: str,
		origin: TransferOrigin,
		existing: list[TransferSessionItem],
		kind: TransferItemKind = TransferItemKind.FILE,
		content_hash: str | None = None,
	) -> TransferStageOutcome:
		digest = content_hash if content_hash is not None else self._hasher.sha256_file(temp_path)
		allocation = allocate_transfer_display_name(requested_name, digest, existing)
		if allocation.disposition is TransferIngestDisposition.SKIPPED_DUPLICATE:
			self._filesystem.delete_file(temp_path)
			match = next(
				item
				for item in existing
				if item.display_name == allocation.display_name and item.content_hash == digest
			)
			return TransferStageOutcome(TransferIngestDisposition.SKIPPED_DUPLICATE, match)

		Path(staging_root).mkdir(parents=True, exist_ok=True)
		staged_path = str(Path(staging_root) / file_id)
		self._filesystem.ensure_parent_directory(staged_path)
		self._filesystem.copy_file(temp_path, staged_path)
		self._filesystem.delete_file(temp_path)
		item = TransferSessionItem(
			file_id=file_id,
			display_name=allocation.display_name,
			staged_path=staged_path,
			content_hash=digest,
			kind=kind,
			origin=origin,
		)
		return TransferStageOutcome(TransferIngestDisposition.ADDED, item)

	def stage_folder_as_zip(
		self,
		staging_root: str,
		*,
		file_id: str,
		folder_path: str,
		origin: TransferOrigin,
		existing: list[TransferSessionItem],
		zip_temp_path: str,
	) -> TransferStageOutcome:
		"""Zip a non-empty folder, then stage the archive as one session item."""
		root = Path(folder_path).expanduser().resolve()
		if count_shareable_files_in_root(root) == 0:
			raise EmptyTransferFolderError(EMPTY_TRANSFER_FOLDER_MESSAGE)
		write_folder_zip(root, Path(zip_temp_path))
		requested = folder_zip_display_name(root.name)
		return self.stage_file(
			staging_root,
			file_id=file_id,
			requested_name=requested,
			temp_path=zip_temp_path,
			origin=origin,
			existing=existing,
			kind=TransferItemKind.FOLDER_ZIP,
		)
