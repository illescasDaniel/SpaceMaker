from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from spacemaker.application.gallery_cache_cleanup import (
	delete_gallery_derived_caches,
	delete_gallery_export_caches,
	sweep_legacy_hash_export_caches,
)
from spacemaker.domain.gallery_index import FileStat, GalleryIndexRow, IndexSyncPlan, plan_index_sync
from spacemaker.domain.library import LibraryFolder
from spacemaker.domain.media import media_kind_for_filename
from spacemaker.ports.outbound.filesystem import FileSystemPort
from spacemaker.ports.outbound.gallery_index import GalleryIndexPort
from spacemaker.ports.outbound.media_probe import MediaProbePort


_log = logging.getLogger(__name__)


class SyncGalleryIndex:
	def __init__(self, filesystem: FileSystemPort, probe: MediaProbePort, index: GalleryIndexPort) -> None:
		self._filesystem = filesystem
		self._probe = probe
		self._index = index

	def _scan_processed(self, library_root: str) -> dict[str, FileStat]:
		processed_root = self._filesystem.library_path(library_root, LibraryFolder.PROCESSED, "")
		on_disk: dict[str, FileStat] = {}
		for relative_path in self._filesystem.list_files_recursive(processed_root):
			try:
				on_disk[relative_path] = self._filesystem.file_stat(
					self._filesystem.library_path(library_root, LibraryFolder.PROCESSED, relative_path)
				)
			except OSError:
				# Vanished or unreadable between listing and stat: skip it, don't abort the whole sync.
				_log.warning("Gallery index sync skipped unreadable file: %s", relative_path)
		return on_disk

	def _build_upserts(
		self, library_root: str, relative_paths: tuple[str, ...], on_disk: dict[str, FileStat]
	) -> list[GalleryIndexRow]:
		upserts: list[GalleryIndexRow] = []
		for relative_path in relative_paths:
			full = self._filesystem.library_path(library_root, LibraryFolder.PROCESSED, relative_path)
			stat = on_disk[relative_path]
			try:
				display = self._probe.display_metadata(full)
			except OSError:
				_log.warning("Gallery index sync skipped unreadable file: %s", relative_path)
				continue
			captured_at = display.captured_at or datetime.fromtimestamp(stat.mtime)
			upserts.append(
				GalleryIndexRow(
					relative_path=relative_path,
					captured_at=captured_at,
					kind=media_kind_for_filename(relative_path),
					mtime=stat.mtime,
					size=stat.size,
					camera_make=display.camera_make,
					camera_model=display.camera_model,
					width=display.width,
					height=display.height,
					duration_seconds=display.duration_seconds,
					gps=display.gps,
				)
			)
		return upserts

	async def run(self, library_root: str) -> IndexSyncPlan:
		# Filesystem walks and metadata probes block; keep them off the event loop.
		on_disk = await asyncio.to_thread(self._scan_processed, library_root)
		indexed = await self._index.snapshot_stats(library_root)
		plan = plan_index_sync(indexed, on_disk)
		if plan.is_empty:
			return plan
		upserts = await asyncio.to_thread(self._build_upserts, library_root, (*plan.added, *plan.changed), on_disk)
		for relative_path in plan.removed:
			delete_gallery_derived_caches(self._filesystem, library_root, relative_path)
		for relative_path in plan.changed:
			delete_gallery_export_caches(self._filesystem, library_root, relative_path)
		if plan.removed or plan.changed:
			sweep_legacy_hash_export_caches(self._filesystem, library_root)
		await self._index.apply_sync(library_root, upserts=upserts, removed=list(plan.removed))
		return plan
