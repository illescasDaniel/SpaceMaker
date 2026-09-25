from __future__ import annotations

from datetime import datetime

from spacemaker.domain.gallery_index import GalleryIndexRow, IndexSyncPlan, plan_index_sync
from spacemaker.domain.library import LibraryFolder
from spacemaker.domain.media import media_kind_for_filename
from spacemaker.ports.outbound.filesystem import FileSystemPort
from spacemaker.ports.outbound.gallery_index import GalleryIndexPort
from spacemaker.ports.outbound.media_probe import MediaProbePort


class SyncGalleryIndex:
	def __init__(self, filesystem: FileSystemPort, probe: MediaProbePort, index: GalleryIndexPort) -> None:
		self._filesystem = filesystem
		self._probe = probe
		self._index = index

	def run(self, library_root: str) -> IndexSyncPlan:
		converted_root = self._filesystem.library_path(library_root, LibraryFolder.CONVERTED, "")
		relative_paths = self._filesystem.list_files_recursive(converted_root)
		on_disk = {
			relative_path: self._filesystem.file_stat(
				self._filesystem.library_path(library_root, LibraryFolder.CONVERTED, relative_path)
			)
			for relative_path in relative_paths
		}
		indexed = self._index.snapshot_stats(library_root)
		plan = plan_index_sync(indexed, on_disk)
		if plan.is_empty:
			return plan
		upserts: list[GalleryIndexRow] = []
		for relative_path in (*plan.added, *plan.changed):
			full = self._filesystem.library_path(library_root, LibraryFolder.CONVERTED, relative_path)
			stat = on_disk[relative_path]
			captured_at = self._probe.captured_at(full) or datetime.fromtimestamp(stat.mtime)
			upserts.append(
				GalleryIndexRow(
					relative_path=relative_path,
					captured_at=captured_at,
					kind=media_kind_for_filename(relative_path),
					mtime=stat.mtime,
					size=stat.size,
				)
			)
		self._index.apply_sync(library_root, upserts=upserts, removed=list(plan.removed))
		return plan
