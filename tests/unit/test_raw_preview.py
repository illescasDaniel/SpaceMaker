from pathlib import Path

from spacemaker.adapters.outbound.media.raw_preview import (
	extract_raw_embedded_jpeg,
	raw_embedded_preview_available,
)


def _write_fake_exiftool(tmp_path: Path) -> Path:
	binary = tmp_path / "exiftool"
	binary.write_text(
		"#!/bin/sh\n"
		'if [ "$1" = "-b" ] && [ "$2" = "-PreviewImage" ]; then\n'
		"  printf '\\377\\330\\377fake-jpeg'\n"
		"  exit 0\n"
		"fi\n"
		"exit 1\n",
	)
	binary.chmod(0o755)
	return binary


def test_given_preview_bytes_when_extract_then_writes_jpeg(tmp_path: Path) -> None:
	source = tmp_path / "photo.dng"
	source.write_bytes(b"fake-dng")
	dest = tmp_path / "preview.jpg"
	exiftool = _write_fake_exiftool(tmp_path)
	assert extract_raw_embedded_jpeg(source=source, destination=dest, exiftool=exiftool) is True
	assert dest.read_bytes().startswith(b"\xff\xd8\xff")


def test_given_exiftool_has_preview_when_available_then_true(tmp_path: Path) -> None:
	source = tmp_path / "photo.dng"
	source.write_bytes(b"fake-dng")
	exiftool = _write_fake_exiftool(tmp_path)
	assert raw_embedded_preview_available(source=source, exiftool=exiftool) is True
