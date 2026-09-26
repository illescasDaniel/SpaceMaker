from __future__ import annotations

from typing import Protocol

from spacemaker.domain.compress_media import compression_tools_available
from spacemaker.domain.managed_tool import ManagedToolStatus, ToolResolution


class _ManagedToolsSnapshot(Protocol):
	def snapshot(self) -> list[ManagedToolStatus]: ...


class ManagedCompressionTools:
	"""CompressionToolsPort adapter over managed-tool / PATH resolution status."""

	def __init__(self, managed_tools: _ManagedToolsSnapshot) -> None:
		self._managed_tools = managed_tools

	def available(self) -> bool:
		resolutions: dict[str, ToolResolution] = {
			item.tool_id: item.resolution for item in self._managed_tools.snapshot()
		}
		return compression_tools_available(resolutions)
