from __future__ import annotations

from datetime import datetime
from typing import Protocol

from spacemaker.domain.gallery_metadata import GalleryDisplayMetadata
from spacemaker.domain.web_compat import VideoProbe


class MediaProbePort(Protocol):
	def probe_video(self, path: str) -> VideoProbe | None: ...

	def image_readable(self, path: str) -> bool: ...

	def output_valid_image(self, path: str) -> bool: ...

	def output_valid_video(self, path: str) -> bool: ...

	def captured_at(self, path: str) -> datetime | None: ...

	def display_metadata(self, path: str) -> GalleryDisplayMetadata: ...
