import sys
from pathlib import Path

import pytest

from spacemaker.adapters.outbound.media.subprocess_converter import SubprocessMediaConverter
from spacemaker.adapters.outbound.media.tool_runner import ToolRunner
from spacemaker.domain.media import is_avifenc_native_extension


_skip_on_windows = pytest.mark.skipif(sys.platform == "win32", reason="Uses POSIX shell scripts")


def _write_exe(path: Path, body: str) -> None:
	path.write_text(body)
	path.chmod(0o755)


@_skip_on_windows
def test_given_avifenc_and_jpeg_when_encode_then_avifenc_progressive_without_magick_rasterize(
	tmp_path: Path,
) -> None:
	# given
	tools = tmp_path / "tools"
	tools.mkdir()
	log = tools / "calls.log"
	_write_exe(
		tools / "avifenc",
		"#!/bin/sh\n"
		f'echo "avifenc $*" >> "{log}"\n'
		"dest=; for a; do dest=$a; done\n"
		'printf "avif" > "$dest"\n',
	)
	_write_exe(
		tools / "magick",
		"#!/bin/sh\n"
		f'echo "magick $*" >> "{log}"\n'
		"exit 1\n",
	)
	_write_exe(
		tools / "exiftool",
		"#!/bin/sh\n"
		f'echo "exiftool $*" >> "{log}"\n'
		"exit 0\n",
	)
	src = tmp_path / "photo.jpg"
	src.write_bytes(b"jpeg-bytes")
	dest = tmp_path / "photo.avif"
	converter = SubprocessMediaConverter(ToolRunner(bundle_root_path=tools, platform_is_windows=False))
	# when
	converter.encode_image_to_avif(str(src), str(dest))
	# then
	assert dest.is_file()
	text = log.read_text()
	assert "avifenc" in text
	assert "--progressive" in text
	assert "magick" not in text


@_skip_on_windows
def test_given_no_avifenc_when_encode_jpeg_then_magick_fallback(tmp_path: Path) -> None:
	# given
	tools = tmp_path / "tools"
	tools.mkdir()
	log = tools / "calls.log"
	_write_exe(
		tools / "magick",
		"#!/bin/sh\n"
		f'echo "magick $*" >> "{log}"\n'
		"dest=; for a; do dest=$a; done\n"
		'printf "avif" > "$dest"\n',
	)
	_write_exe(tools / "exiftool", "#!/bin/sh\nexit 0\n")
	src = tmp_path / "photo.jpg"
	src.write_bytes(b"jpeg-bytes")
	dest = tmp_path / "photo.avif"
	converter = SubprocessMediaConverter(ToolRunner(bundle_root_path=tools, platform_is_windows=False))
	# when
	converter.encode_image_to_avif(str(src), str(dest))
	# then
	assert dest.is_file()
	assert "magick" in log.read_text()


def test_given_jpeg_png_when_avifenc_native_then_true() -> None:
	assert is_avifenc_native_extension("jpg")
	assert is_avifenc_native_extension("JPEG")
	assert is_avifenc_native_extension("png")
	assert not is_avifenc_native_extension("heic")
	assert not is_avifenc_native_extension("webp")
