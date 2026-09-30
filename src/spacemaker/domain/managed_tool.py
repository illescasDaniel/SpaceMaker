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


class ToolsSummaryStatus(StrEnum):
	"""Aggregate Components chip: all resolved (ok) / anything unresolved (missing).

	WARNING is retained for legacy clients but is not emitted by current summary rules.
	"""

	OK = "ok"
	WARNING = "warning"
	MISSING = "missing"


@dataclass(frozen=True)
class ManagedToolStatus:
	tool_id: str
	phase: ToolInstallPhase
	resolution: ToolResolution
	path: str | None = None
	message: str | None = None
	# Display-only OS/distro package-manager one-liner when failed/missing; never executed by the app.
	install_command: str | None = None


def summarize_tool_resolutions(resolutions: list[ToolResolution]) -> ToolsSummaryStatus:
	"""Map per-tool resolutions to the Components aggregate chip.

	OK when every tool resolves (managed or PATH); MISSING when any is unresolved.
	"""
	if any(item is ToolResolution.MISSING for item in resolutions):
		return ToolsSummaryStatus.MISSING
	return ToolsSummaryStatus.OK


def tools_summary_line(*, managed: int, path: int, missing: int) -> str:
	return f"{managed} ready · {path} system · {missing} missing"
