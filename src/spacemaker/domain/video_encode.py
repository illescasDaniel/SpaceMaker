from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath

from spacemaker.domain.web_compat import VideoProbe, is_web_compatible_video


# Codecs reliably playable inline in Chromium/WebKit gallery (HEVC excluded).
INLINE_PREVIEW_VIDEO_CODECS: frozenset[str] = frozenset({"h264", "av1", "vp9"})


class HardwareVideoEncoder(StrEnum):
	NONE = "none"
	AV1 = "av1"
	H264 = "h264"


def is_inline_preview_video(probe: VideoProbe | None) -> bool:
	if probe is None:
		return False
	if not is_web_compatible_video(probe):
		return False
	return probe.video_codec.lower() in INLINE_PREVIEW_VIDEO_CODECS


def _relative_parent_stem(relative_path: str) -> tuple[str, str]:
	parts = PurePosixPath(relative_path)
	stem = parts.stem
	parent = str(parts.parent)
	if parent == ".":
		parent = ""
	return parent, stem


def video_h264_web_relative_path(relative_source: str) -> str:
	parent, stem = _relative_parent_stem(relative_source)
	filename = f"{stem}.h264.mp4"
	if parent:
		return f"{parent}/{filename}"
	return filename


def is_library_h264_output_path(relative_path: str) -> bool:
	return relative_path.lower().endswith(".h264.mp4")


def is_library_av1_output_path(relative_path: str) -> bool:
	return relative_path.lower().endswith(".av1.mp4")
