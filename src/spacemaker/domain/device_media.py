"""Which device file names are previewable photos or videos. Depends on nothing, so both ``device_browse`` (listing
counts) and ``device_preview`` (preview pipeline) can import it without a cycle."""

from __future__ import annotations


PREVIEWABLE_IMAGE_EXTENSIONS: frozenset[str] = frozenset({"jpg", "jpeg", "png", "webp", "gif", "heic", "heif"})
"""Lower-case, without the dot."""

PREVIEWABLE_VIDEO_EXTENSIONS: frozenset[str] = frozenset({"mp4", "mov", "m4v", "3gp", "mkv", "webm"})
"""Lower-case, without the dot."""


def is_media_name(name: str) -> bool:
	"""True when ``name`` has a previewable photo or video extension (case-insensitive)."""
	if "." not in name:
		return False
	extension = name.rsplit(".", 1)[-1].lower()
	return extension in PREVIEWABLE_IMAGE_EXTENSIONS or extension in PREVIEWABLE_VIDEO_EXTENSIONS


__all__ = ["PREVIEWABLE_IMAGE_EXTENSIONS", "PREVIEWABLE_VIDEO_EXTENSIONS", "is_media_name"]
