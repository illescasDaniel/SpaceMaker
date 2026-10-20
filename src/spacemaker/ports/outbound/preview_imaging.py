from __future__ import annotations

from typing import Protocol


class PreviewImagingPort(Protocol):
	"""Image decoding for device previews (arbitrary, untrusted bytes; always re-encodes to JPEG)."""

	def thumbnail_from_head(self, head: bytes, max_edge: int) -> bytes | None:
		"""JPEG (longest edge <= ``max_edge``, EXIF Orientation applied) from the embedded EXIF/HEIC
		thumbnail found in ``head`` (first bytes of a file); ``None`` when absent or undecodable. Never raises.
		"""
		...

	def render_jpeg(self, source_path: str, max_edge: int, timeout_s: float) -> bytes:
		"""Fit-within, auto-oriented JPEG of the image file at ``source_path`` (a local temp file).

		Decodes in a subprocess bounded by ``timeout_s`` and a pixel-dimension limit. Raises
		``DevicePreviewError`` (``NO_PREVIEW`` when undecodable/over the pixel limit, ``TIMEOUT`` on timeout).
		"""
		...
