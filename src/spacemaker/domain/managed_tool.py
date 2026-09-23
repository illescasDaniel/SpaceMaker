from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ToolResolution(StrEnum):
	MANAGED = "managed"
	PATH = "path"
	MISSING = "missing"


class ToolInstallPhase(StrEnum):
	IDLE = "idle"
	DOWNLOADING = "downloading"
	READY = "ready"
	FAILED = "failed"


@dataclass(frozen=True)
class ManagedToolStatus:
	tool_id: str
	phase: ToolInstallPhase
	resolution: ToolResolution
	path: str | None = None
	message: str | None = None
