from __future__ import annotations

from enum import StrEnum


class MediaKind(StrEnum):
	IMAGE = "image"
	VIDEO = "video"
	UNSUPPORTED = "unsupported"


IMAGE_EXTENSIONS: frozenset[str] = frozenset(
	{
		"jpg",
		"jpeg",
		"png",
		"webp",
		"tiff",
		"jxl",
		"heic",
		"heif",
		"dng",
		"avif",
		"cr2",
		"cr3",
		"nef",
		"nrw",
		"arw",
		"srf",
		"sr2",
		"raf",
		"orf",
		"rw2",
		"pef",
		"srw",
	}
)

VIDEO_EXTENSIONS: frozenset[str] = frozenset(
	{
		"mp4",
		"mov",
		"mkv",
		"webm",
		"avi",
		"m4v",
		"mts",
		"m2ts",
	}
)

RAW_EXTENSIONS: frozenset[str] = frozenset(
	{
		"dng",
		"cr2",
		"cr3",
		"nef",
		"nrw",
		"arw",
		"srf",
		"sr2",
		"raf",
		"orf",
		"rw2",
		"pef",
		"srw",
	}
)

JPEG_EXTENSIONS: frozenset[str] = frozenset({"jpg", "jpeg"})

WEB_VIDEO_CONTAINERS: frozenset[str] = frozenset({"mp4", "webm", "mov"})
WEB_VIDEO_CODECS: frozenset[str] = frozenset({"h264", "hevc", "vp9", "av1"})
WEB_AUDIO_CODECS: frozenset[str] = frozenset({"aac", "mp3", "opus", "vorbis", "flac"})
WEB_IMAGE_EXTENSIONS: frozenset[str] = frozenset({"jpg", "jpeg", "png", "webp", "gif", "avif"})

LOW_BITRATE_BPS = 1_500_000
SIZE_ROLLBACK_NUMERATOR = 11
SIZE_ROLLBACK_DENOMINATOR = 10


def normalize_extension(filename: str) -> str:
	if "." not in filename:
		return ""
	return filename.rsplit(".", 1)[-1].lower()


def media_kind_for_extension(ext: str) -> MediaKind:
	ext = ext.lower()
	if ext in IMAGE_EXTENSIONS:
		return MediaKind.IMAGE
	if ext in VIDEO_EXTENSIONS:
		return MediaKind.VIDEO
	return MediaKind.UNSUPPORTED


def is_raw_extension(ext: str) -> bool:
	return ext.lower() in RAW_EXTENSIONS
