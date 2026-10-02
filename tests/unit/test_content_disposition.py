from pathlib import Path

from spacemaker.adapters.inbound.web.media_paths import _attachment_filename, _content_disposition


def test_given_ascii_name_when_disposition_then_plain_filename():
	# given
	path = Path("a/IMG_1.jpg")
	# when
	value = _attachment_filename(path)
	# then
	assert value == 'attachment; filename="IMG_1.jpg"'


def test_given_non_ascii_name_when_disposition_then_header_is_latin1_with_rfc5987_name():
	# given
	path = Path("Ñandú 写真.jpg")
	# when
	value = _attachment_filename(path)
	# then
	value.encode("latin-1")
	assert "filename*=UTF-8''%C3%91and%C3%BA%20%E5%86%99%E7%9C%9F.jpg" in value


def test_given_quote_and_newline_when_disposition_then_stripped():
	# given
	name = 'a"b\r\nc.jpg'
	# when
	value = _content_disposition("inline", name)
	# then
	assert "\n" not in value and "\r" not in value
	assert value == 'inline; filename="abc.jpg"'
