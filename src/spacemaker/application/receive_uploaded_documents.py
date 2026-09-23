from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from spacemaker.domain.upload_paths import normalize_upload_relative_path
from spacemaker.ports.outbound.filesystem import FileSystemPort


class DocumentUploadDisposition(StrEnum):
	SAVED = "saved"
	SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class DocumentUploadOutcome:
	disposition: DocumentUploadDisposition
	relative_path: str


class ReceiveUploadedDocuments:
	def __init__(self, filesystem: FileSystemPort) -> None:
		self._filesystem = filesystem

	def ingest(
		self,
		dest_root: str,
		raw_relative: str,
		*,
		temp_path: str,
		incoming_size: int,
	) -> DocumentUploadOutcome:
		relative = normalize_upload_relative_path(raw_relative)
		if relative is None:
			raise ValueError("invalid upload path")
		Path(dest_root).mkdir(parents=True, exist_ok=True)
		dest = str(Path(dest_root) / Path(relative))
		if self._should_skip(dest, incoming_size):
			self._filesystem.delete_file(temp_path)
			return DocumentUploadOutcome(DocumentUploadDisposition.SKIPPED, relative)
		self._filesystem.ensure_parent_directory(dest)
		self._filesystem.copy_file(temp_path, dest)
		self._filesystem.delete_file(temp_path)
		return DocumentUploadOutcome(DocumentUploadDisposition.SAVED, relative)

	def _should_skip(self, dest: str, incoming_size: int) -> bool:
		if not self._filesystem.exists(dest):
			return False
		local = self._filesystem.file_size(dest)
		return incoming_size > 0 and local == incoming_size
