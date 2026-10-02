from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath

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
	if PureWindowsPath(relative).drive:
		# `C:\x` or `C:x`: on Windows a drive-qualified right-hand side replaces the base path.
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
