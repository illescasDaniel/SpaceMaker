from __future__ import annotations

from io import BytesIO

import segno


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
