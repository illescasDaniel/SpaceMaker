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

	def render_embedded_jpeg(self, jpeg: bytes, max_edge: int, fallback_orientation: int, timeout_s: float) -> bytes:
		"""Fit-within JPEG (longest edge <= ``max_edge``, **never enlarged**) from an embedded preview JPEG held in
		memory (e.g. a DNG's preview, untrusted bytes).

		Orientation is applied exactly once: the JPEG's own EXIF Orientation when it has one, otherwise
		``fallback_orientation`` (the DNG's IFD0 value, 1-8; 1 = as stored). No EXIF is written. Decodes in a
		subprocess bounded by ``timeout_s`` and the same pixel-dimension limit as ``render_jpeg``. Raises
		``DevicePreviewError`` (``NO_PREVIEW`` when undecodable/over the pixel limit, ``TIMEOUT`` on timeout).
		"""
		...
