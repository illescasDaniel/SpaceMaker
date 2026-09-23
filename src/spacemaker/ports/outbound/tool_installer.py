from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ToolInstallResult:
	tool_id: str
	ok: bool
	message: str = ""


class ToolInstallerPort(Protocol):
	def install(self, tool_id: str) -> ToolInstallResult:
		"""Download and place one tool into the managed tools directory."""
		...

	def has_catalog_entry(self, tool_id: str) -> bool: ...

	def catalog_covers(self, tool_id: str) -> bool: ...
