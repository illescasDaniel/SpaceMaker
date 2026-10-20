from __future__ import annotations

import threading
from typing import Protocol

from spacemaker.domain.device_preview import VideoPoster


class VideoPosterPort(Protocol):
	"""First-frame extraction for device videos (arbitrary, untrusted media; always re-encodes to JPEG)."""

	def render_poster(
		self, source_url: str, max_edge: int, timeout_s: float, cancel: threading.Event | None = None
	) -> VideoPoster:
		"""Fit-within JPEG (longest edge <= ``max_edge``, rotation metadata applied) of the first frame of
		the media at ``source_url`` (a loopback range-streaming URL), with the duration from the same run.

		Bounded by ``timeout_s``; setting ``cancel`` aborts the run early. Raises ``DevicePreviewError``:
		``NO_PREVIEW`` (undecodable or no video stream), ``TIMEOUT``, ``DEVICE_BUSY`` when the source
		answered 409 and ``UNPLUGGED`` when it answered 503 (the adapter learns this from the tool's HTTP
		error text, e.g. ffmpeg's ``Server returned 409 Conflict``).
		"""
		...
