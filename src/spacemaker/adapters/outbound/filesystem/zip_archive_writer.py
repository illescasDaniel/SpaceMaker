from __future__ import annotations

import os
import uuid
import zipfile
from collections.abc import Sequence
from pathlib import Path

from spacemaker.domain.gallery_batch import ArchiveEntry


class StoredZipArchiveWriter:
	"""Streams files into an uncompressed zip (JPEG/MP4 are already compressed), never holding them in memory."""

	def write_stored_zip(
		self,
		destination: str,
		entries: Sequence[ArchiveEntry],
		*,
		skip_missing: bool = False,
	) -> int:
		target = Path(destination)
		target.parent.mkdir(parents=True, exist_ok=True)
		staging = target.with_name(f".{uuid.uuid4().hex}.partial{target.suffix}")
		written = 0
		try:
			with zipfile.ZipFile(staging, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
				for entry in entries:
					try:
						archive.write(entry.source_path, arcname=entry.entry_name)
					except FileNotFoundError:
						if not skip_missing:
							raise
						continue
					written += 1
			os.replace(staging, target)
			return written
		finally:
			staging.unlink(missing_ok=True)
