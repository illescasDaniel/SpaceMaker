from __future__ import annotations

from typing import Protocol


class MediaConverterPort(Protocol):
	def encode_image_to_avif(self, source: str, destination: str) -> None: ...

	def encode_video_to_av1(self, source: str, destination: str) -> None: ...
