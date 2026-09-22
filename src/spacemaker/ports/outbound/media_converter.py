from __future__ import annotations

from collections.abc import Callable
from typing import Protocol


class MediaConverterPort(Protocol):
	def encode_image_to_avif(self, source: str, destination: str) -> None: ...

	def encode_video_to_av1(self, source: str, destination: str) -> None: ...

	def encode_image_to_jpeg(self, source: str, destination: str) -> None: ...

	def encode_video_to_h264_aac(
		self,
		source: str,
		destination: str,
		*,
		on_progress: Callable[[int], None] | None = None,
	) -> None: ...
