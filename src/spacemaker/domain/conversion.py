from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath

from spacemaker.domain.media import (
	JPEG_EXTENSIONS,
	SIZE_ROLLBACK_DENOMINATOR,
	SIZE_ROLLBACK_NUMERATOR,
	MediaKind,
	media_kind_for_extension,
	normalize_extension,
)
from spacemaker.domain.web_compat import VideoProbe, is_low_bitrate_web_video, is_web_compatible_video


class ConversionRoute(StrEnum):
	MOVE_AS_IS = "move_as_is"
	ENCODE = "encode"
	INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class PlannedOutput:
	relative_path: str


def relative_parent_stem(relative_path: str) -> tuple[str, str]:
	parts = PurePosixPath(relative_path)
	stem = parts.stem
	parent = str(parts.parent)
	if parent == ".":
		parent = ""
	return parent, stem


def image_avif_relative_path(
	relative_source: str,
	*,
	collision_avif_exists: bool,
) -> str:
	parent, stem = relative_parent_stem(relative_source)
	ext = normalize_extension(relative_source)
	filename = f"{stem}.avif"
	if collision_avif_exists and ext in JPEG_EXTENSIONS:
		filename = f"{stem}_{ext}.avif"
	if parent:
		return f"{parent}/{filename}"
	return filename


def video_av1_relative_path(relative_source: str) -> str:
	parent, stem = relative_parent_stem(relative_source)
	filename = f"{stem}.av1.mp4"
	if parent:
		return f"{parent}/{filename}"
	return filename


def route_before_encode(
	relative_path: str,
	*,
	video_probe: VideoProbe | None,
) -> ConversionRoute:
	ext = normalize_extension(relative_path)
	kind = media_kind_for_extension(ext)
	if kind is MediaKind.UNSUPPORTED:
		return ConversionRoute.INVALID
	if kind is MediaKind.IMAGE:
		if ext == "avif":
			return ConversionRoute.MOVE_AS_IS
		return ConversionRoute.ENCODE
	# video
	lower = relative_path.lower()
	if lower.endswith(".av1.mp4"):
		return ConversionRoute.MOVE_AS_IS
	if video_probe is None:
		return ConversionRoute.ENCODE
	if video_probe.video_codec.lower() == "av1" and is_web_compatible_video(video_probe):
		return ConversionRoute.MOVE_AS_IS
	if is_low_bitrate_web_video(video_probe):
		return ConversionRoute.MOVE_AS_IS
	return ConversionRoute.ENCODE


def output_exceeds_rollback_threshold(source_size: int, output_size: int) -> bool:
	if source_size <= 0:
		return False
	limit = source_size * SIZE_ROLLBACK_NUMERATOR // SIZE_ROLLBACK_DENOMINATOR
	return output_size > limit
