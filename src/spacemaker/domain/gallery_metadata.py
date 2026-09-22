from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class GalleryDisplayMetadata:
	filename: str
	captured_at: datetime | None
	camera_make: str
	camera_model: str
	width: int | None
	height: int | None
	duration_seconds: float | None
	file_size_bytes: int
	gps: str
