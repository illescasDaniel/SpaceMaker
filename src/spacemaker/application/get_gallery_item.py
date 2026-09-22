from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from spacemaker.domain.gallery import GalleryItem, gallery_item
from spacemaker.domain.gallery_metadata import GalleryDisplayMetadata
from spacemaker.domain.library import LibraryFolder
from spacemaker.domain.media import MediaKind
from spacemaker.domain.video_encode import is_inline_preview_video
from spacemaker.ports.outbound.filesystem import FileSystemPort
from spacemaker.ports.outbound.media_probe import MediaProbePort


@dataclass(frozen=True, slots=True)
class GalleryItemDetail:
	item: GalleryItem
	metadata: GalleryDisplayMetadata
	absolute_path: str
	preview_in_browser: bool


class GetGalleryItem:
	def __init__(self, filesystem: FileSystemPort, probe: MediaProbePort) -> None:
		self._filesystem = filesystem
		self._probe = probe

	def get(
		self,
		library_root: str,
		relative_path: str,
		*,
		captured_at: datetime | None = None,
	) -> GalleryItemDetail | None:
		full = self._filesystem.library_path(library_root, LibraryFolder.CONVERTED, relative_path)
		if not self._filesystem.exists(full):
			return None
		path = Path(full)
		when = captured_at
		if when is None:
			when = self._probe.captured_at(str(path))
		if when is None:
			when = datetime.fromtimestamp(path.stat().st_mtime)
		item = gallery_item(relative_path=relative_path, captured_at=when)
		meta = self._probe.display_metadata(full)
		preview = True
		if item.kind is MediaKind.VIDEO:
			probe = self._probe.probe_video(full)
			preview = is_inline_preview_video(probe)
		return GalleryItemDetail(
			item=item,
			metadata=meta,
			absolute_path=str(path.resolve()),
			preview_in_browser=preview,
		)
