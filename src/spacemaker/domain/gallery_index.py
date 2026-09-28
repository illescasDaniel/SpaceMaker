from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath

from spacemaker.domain.gallery import GalleryItem
from spacemaker.domain.gallery_metadata import GalleryDisplayMetadata
from spacemaker.domain.media import MediaKind


def to_epoch_seconds(value: datetime) -> float:
	# datetime.timestamp()/fromtimestamp() go through the OS's local mktime, which raises
	# OSError on Windows for dates at/before 1970 — including the epoch fallback used when
	# EXIF/probe metadata is unavailable. A fixed UTC offset applied in Python avoids that.
	return value.replace(tzinfo=timezone.utc).timestamp()


def from_epoch_seconds(seconds: float) -> datetime:
	return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(tzinfo=None)


@dataclass(frozen=True, slots=True)
class FileStat:
	mtime: float
	size: int


@dataclass(frozen=True, slots=True)
class GalleryIndexRow:
	relative_path: str
	captured_at: datetime
	kind: MediaKind
	mtime: float
	size: int
	# Display fields probed at index sync so item open need not re-run ExifTool/ffprobe.
	camera_make: str = ""
	camera_model: str = ""
	width: int | None = None
	height: int | None = None
	duration_seconds: float | None = None
	gps: str = ""

	def as_item(self) -> GalleryItem:
		return GalleryItem(relative_path=self.relative_path, captured_at=self.captured_at, kind=self.kind)

	def as_display_metadata(self) -> GalleryDisplayMetadata:
		return GalleryDisplayMetadata(
			filename=PurePosixPath(self.relative_path).name,
			captured_at=self.captured_at,
			camera_make=self.camera_make,
			camera_model=self.camera_model,
			width=self.width,
			height=self.height,
			duration_seconds=self.duration_seconds,
			file_size_bytes=self.size,
			gps=self.gps,
		)


@dataclass(frozen=True, slots=True)
class IndexSyncPlan:
	added: tuple[str, ...]
	changed: tuple[str, ...]
	removed: tuple[str, ...]

	@property
	def is_empty(self) -> bool:
		return not (self.added or self.changed or self.removed)


def plan_index_sync(indexed: dict[str, FileStat], on_disk: dict[str, FileStat]) -> IndexSyncPlan:
	added = sorted(path for path in on_disk if path not in indexed)
	removed = sorted(path for path in indexed if path not in on_disk)
	changed = sorted(path for path in on_disk if path in indexed and on_disk[path] != indexed[path])
	return IndexSyncPlan(added=tuple(added), changed=tuple(changed), removed=tuple(removed))


@dataclass(frozen=True, slots=True)
class GalleryCursor:
	captured_at: datetime
	relative_path: str

	def encode(self) -> str:
		raw = json.dumps([to_epoch_seconds(self.captured_at), self.relative_path])
		return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")

	@staticmethod
	def decode(raw: str) -> GalleryCursor:
		timestamp, relative_path = json.loads(base64.urlsafe_b64decode(raw.encode("ascii")).decode("utf-8"))
		return GalleryCursor(captured_at=from_epoch_seconds(timestamp), relative_path=relative_path)


@dataclass(frozen=True, slots=True)
class GalleryPage:
	items: tuple[GalleryItem, ...]
	next_cursor: str | None
