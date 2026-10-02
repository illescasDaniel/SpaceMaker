from __future__ import annotations

from io import BytesIO

import segno
from fastapi import Response


def qr_svg_response(payload: str) -> Response:
	"""QR as an uncacheable response: its content changes when the network passcode does."""
	return Response(
		content=encode_qr_svg(payload),
		media_type="image/svg+xml",
		headers={"Cache-Control": "no-store"},
	)


def encode_qr_svg(payload: str, *, scale: int = 8) -> bytes:
	"""SVG QR with opaque white background (readable on dark UI themes)."""
	buffer = BytesIO()
	segno.make(payload).save(
		buffer,
		kind="svg",
		scale=scale,
		dark="#000000",
		light="#ffffff",
	)
	return buffer.getvalue()
