from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from spacemaker.domain.library import LibraryFolder
from spacemaker.domain.upload_paths import normalize_upload_relative_path
from spacemaker.ports.outbound.filesystem import FileSystemPort


class UploadDisposition(StrEnum):
	SAVED = "saved"
	SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class UploadOutcome:
	disposition: UploadDisposition
	relative_path: str


class ReceiveUploadedMedia:
	def __init__(self, filesystem: FileSystemPort) -> None:
		self._filesystem = filesystem

	def ingest(
		self,
		library_root: str,
		raw_relative: str,
		*,
		temp_path: str,
		incoming_size: int,
	) -> UploadOutcome:
		relative = normalize_upload_relative_path(raw_relative)
		if relative is None:
			raise ValueError("invalid upload path")
		self._filesystem.ensure_library_folders(library_root)
		dest = self._filesystem.library_path(library_root, LibraryFolder.ORIGINALS, relative)
		if self._should_skip(dest, incoming_size):
			self._filesystem.delete_file(temp_path)
			return UploadOutcome(UploadDisposition.SKIPPED, relative)
		self._filesystem.copy_file(temp_path, dest)
		self._filesystem.delete_file(temp_path)
		return UploadOutcome(UploadDisposition.SAVED, relative)

	def _should_skip(self, dest: str, incoming_size: int) -> bool:
		if not self._filesystem.exists(dest):
			return False
		local = self._filesystem.file_size(dest)
		return incoming_size > 0 and local == incoming_size
