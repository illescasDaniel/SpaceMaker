from spacemaker.adapters.inbound.web.qr_svg import encode_qr_svg


def test_given_payload_when_encode_qr_svg_then_white_background() -> None:
	svg = encode_qr_svg("http://example.test/gallery", scale=2).decode("utf-8")
	assert 'fill="#fff"' in svg or 'fill="#ffffff"' in svg
	assert 'stroke="#000"' in svg or 'stroke="#000000"' in svg
