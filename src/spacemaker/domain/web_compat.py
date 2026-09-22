from __future__ import annotations

from dataclasses import dataclass

from spacemaker.domain.media import (
	WEB_AUDIO_CODECS,
	WEB_IMAGE_EXTENSIONS,
	WEB_VIDEO_CODECS,
	WEB_VIDEO_CONTAINERS,
	normalize_extension,
)


@dataclass(frozen=True, slots=True)
class VideoProbe:
	container_ext: str
	video_codec: str
	audio_codec: str | None
	bitrate_bps: int


def is_web_compatible_video(probe: VideoProbe) -> bool:
	container = probe.container_ext.lower()
	if container not in WEB_VIDEO_CONTAINERS:
		return False
	if probe.video_codec.lower() not in WEB_VIDEO_CODECS:
		return False
	if probe.audio_codec is not None and probe.audio_codec.lower() not in WEB_AUDIO_CODECS:
		return False
	return True


def is_web_compatible_image_for_rollback(filename: str) -> bool:
	return normalize_extension(filename) in WEB_IMAGE_EXTENSIONS


def is_low_bitrate_web_video(probe: VideoProbe) -> bool:
	if not is_web_compatible_video(probe):
		return False
	return probe.bitrate_bps > 0 and probe.bitrate_bps <= 1_500_000
