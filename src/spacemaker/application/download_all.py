from __future__ import annotations

import os
from collections.abc import Iterator, Sequence
from pathlib import Path

from spacemaker.domain.download_all import (
	DownloadAllBuildError,
	DownloadAllItem,
	DownloadAllKind,
	NothingToDownloadError,
	dedupe_entry_names,
	sanitize_entry_name,
)
from spacemaker.domain.gallery_batch import ArchiveEntry
from spacemaker.ports.outbound.archive_writer import ArchiveWriterPort


class DownloadAll:
	"""Build one zip of every file in a Share or Transfer manifest."""

	def __init__(self, archive_writer: ArchiveWriterPort) -> None:
		self._archive_writer = archive_writer

	def build(self, kind: DownloadAllKind, items: Sequence[DownloadAllItem], destination: str) -> None:
		"""Write the archive for ``items`` to ``destination``.

		Expands folder items to their files (relative paths under ``<folder>/``), sanitizes and
		dedupes entry names, and calls ``write_stored_zip(skip_missing=True)``. Raises
		``NothingToDownloadError`` when there are no entries (before or after skipping missing files)
		and wraps ``OSError`` as ``DownloadAllBuildError``.
		"""
		try:
			raw = list(self._raw_entries(items))
		except OSError as exc:
			raise DownloadAllBuildError(str(exc)) from exc
		if not raw:
			raise NothingToDownloadError("nothing to download")
		names = dedupe_entry_names([sanitize_entry_name(name) for name, _source in raw])
		entries = [ArchiveEntry(source, name) for name, (_raw_name, source) in zip(names, raw, strict=True)]
		try:
			written = self._archive_writer.write_stored_zip(destination, entries, skip_missing=True)
		except OSError as exc:
			raise DownloadAllBuildError(str(exc)) from exc
		if written < 1:
			Path(destination).unlink(missing_ok=True)
			raise NothingToDownloadError("nothing to download")

	@staticmethod
	def _raw_entries(items: Sequence[DownloadAllItem]) -> Iterator[tuple[str, str]]:
		"""Yield ``(entry name, source path)``; folder rows expand to their files under ``<name>/``."""
		for item in items:
			if not item.is_folder:
				if Path(item.source_path).is_file():
					yield item.name, item.source_path
				continue
			root = Path(item.source_path)
			for current, dirs, files in os.walk(root):
				dirs.sort()
				for filename in sorted(files):
					full = Path(current) / filename
					relative = full.relative_to(root).as_posix()
					yield f"{item.name}/{relative}", str(full)
