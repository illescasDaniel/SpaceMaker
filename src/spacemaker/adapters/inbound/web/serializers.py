from __future__ import annotations

from typing import TypedDict

from spacemaker.domain.gallery import GalleryItem
from spacemaker.domain.gallery_metadata import GalleryDisplayMetadata


class GalleryItemPayload(TypedDict):
	relative_path: str
	captured_at: str
	kind: str


class GalleryMetadataPayload(TypedDict):
	filename: str
	captured_at: str | None
	camera_make: str
	camera_model: str
	width: int | None
	height: int | None
	duration_seconds: float | None
	file_size_bytes: int
	gps: str


def gallery_item_dict(item: GalleryItem) -> GalleryItemPayload:
	return {
		"relative_path": item.relative_path,
		"captured_at": item.captured_at.isoformat(),
		"kind": item.kind.value,
	}


def metadata_dict(meta: GalleryDisplayMetadata) -> GalleryMetadataPayload:
	return {
		"filename": meta.filename,
		"captured_at": meta.captured_at.isoformat() if meta.captured_at else None,
		"camera_make": meta.camera_make,
		"camera_model": meta.camera_model,
		"width": meta.width,
		"height": meta.height,
		"duration_seconds": meta.duration_seconds,
		"file_size_bytes": meta.file_size_bytes,
		"gps": meta.gps,
	}


# Keep private aliases for call sites that still use the original names.
_gallery_item_dict = gallery_item_dict
_metadata_dict = metadata_dict
