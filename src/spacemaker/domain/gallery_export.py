from __future__ import annotations

import hashlib
from enum import StrEnum
from pathlib import PurePosixPath

from spacemaker.domain.media import JPEG_EXTENSIONS, normalize_extension
from spacemaker.domain.web_compat import VideoProbe, is_web_compatible_video


class ExportFormat(StrEnum):
	JPEG = "jpeg"
	H264_AAC = "h264_aac"


class ExportJobPhase(StrEnum):
	IDLE = "idle"
	RUNNING = "running"
	DONE = "done"
	ERROR = "error"


def is_safe_gallery_relative_path(relative: str) -> bool:
	if not relative or relative.startswith("/") or relative.startswith("\\"):
		return False
	normalized = relative.replace("\\", "/")
	parts = PurePosixPath(normalized).parts
	return ".." not in parts


def is_friendly_jpeg_filename(filename: str) -> bool:
	return normalize_extension(filename) in JPEG_EXTENSIONS


def is_friendly_h264_aac_mp4(probe: VideoProbe | None) -> bool:
	if probe is None:
		return False
	if probe.container_ext.lower() != "mp4":
		return False
	if probe.video_codec.lower() != "h264":
		return False
	if probe.audio_codec is not None and probe.audio_codec.lower() != "aac":
		return False
	return is_web_compatible_video(probe)


def export_cache_filename(
	relative_path: str,
	source_mtime_ns: int,
	source_size: int,
	export_format: ExportFormat,
) -> str:
	ext = "jpg" if export_format is ExportFormat.JPEG else "mp4"
	key = f"{relative_path}\0{source_mtime_ns}\0{source_size}\0{export_format.value}"
	digest = hashlib.sha256(key.encode()).hexdigest()[:20]
	return f"{digest}.{ext}"
