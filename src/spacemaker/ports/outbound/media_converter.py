from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from spacemaker.domain.gallery_batch import VideoExportEncoder
from spacemaker.domain.video_encode import HardwareVideoEncoder


class FriendlyVideoExportPort(Protocol):
	"""Outbound: which encoder a gallery friendly MP4 export would use (spec: gallery-batch).

	Separate from ``MediaConverterPort.library_video_encoder`` because library convert stays
	hardware-only while the gallery export may fall back to the CPU after user confirmation.
	``MediaConverterPort.encode_video_to_h264_aac`` takes ``use_cpu=True`` to encode with ``libx264``.
	"""

	def friendly_video_encoder(self) -> VideoExportEncoder:
		"""HARDWARE_H264 if a hardware H.264 encoder works, else CPU_H264 if ffmpeg has libx264, else NONE."""
		...


class MediaConverterPort(FriendlyVideoExportPort, Protocol):
	"""Outbound media encode. Image AVIF prefers progressive avifenc when available."""

	def library_video_encoder(self) -> HardwareVideoEncoder: ...

	def encode_image_to_avif(self, source: str, destination: str) -> None: ...

	def encode_video_to_av1(self, source: str, destination: str) -> None: ...

	def encode_image_to_jpeg(self, source: str, destination: str) -> None: ...

	def encode_video_to_h264_aac(
		self,
		source: str,
		destination: str,
		*,
		on_progress: Callable[[int], None] | None = None,
		use_cpu: bool = False,
	) -> None: ...
