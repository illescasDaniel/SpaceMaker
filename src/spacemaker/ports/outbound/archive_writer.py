from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from spacemaker.domain.gallery_batch import ArchiveEntry


class ArchiveWriterPort(Protocol):
	"""Outbound: write a zip archive of existing files, streamed from disk, never held in memory."""

	def write_stored_zip(
		self,
		destination: str,
		entries: Sequence[ArchiveEntry],
		*,
		skip_missing: bool = False,
	) -> int:
		"""Write ``entries`` uncompressed (JPEG/MP4 are already compressed) to ``destination``.

		Writes to a temporary file beside ``destination`` and renames on success so a failed run
		never leaves a half-written archive. Returns the number of entries written. With
		``skip_missing`` an entry whose source file no longer exists is skipped instead of failing.
		"""
		...
