from __future__ import annotations

from typing import Protocol


class CompressionToolsPort(Protocol):
	"""Whether library compression CLIs (magick + ffmpeg) can be resolved.

	Hardware video encoders are not required — videos may move-as-is or use
	H.264 hardware per convert-media. Adapters typically wrap managed-tool /
	PATH resolution and map to domain ``compression_tools_available``.
	"""

	def available(self) -> bool: ...
