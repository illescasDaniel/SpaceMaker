from __future__ import annotations

import subprocess

import pytest

from spacemaker.adapters.outbound.media.subprocess_preview_imaging import SubprocessPreviewImaging
from spacemaker.domain.device_preview import DevicePreviewError, DevicePreviewErrorKind


class _RecordingImaging(SubprocessPreviewImaging):
	def __init__(self) -> None:
		super().__init__()
		self.calls: list[list[str]] = []

	def _run_magick(self, args: list[str], stdin: bytes | None, timeout_s: float) -> bytes:
		self.calls.append(args)
		return b"jpeg"


@pytest.mark.parametrize(
	("name", "prefix"),
	[
		("a.jpg", "jpeg:"),
		("a.JPEG", "jpeg:"),
		("a.png", "png:"),
		("a.webp", "webp:"),
		("a.gif", "gif:"),
		("a.heic", "heic:"),
		("a.heif", "heic:"),
	],
)
def test_given_known_extension_when_render_jpeg_then_source_gets_explicit_coder_prefix(name: str, prefix: str) -> None:
	# given
	imaging = _RecordingImaging()
	# when
	imaging.render_jpeg(f"/fake/{name}", 320, 5.0)
	# then
	assert f"{prefix}/fake/{name}[0]" in imaging.calls[0]


@pytest.mark.parametrize("name", ["a.svg", "a.mvg", "a", "a.txt"])
def test_given_unknown_extension_when_render_jpeg_then_no_preview_without_spawning(name: str) -> None:
	# given
	imaging = _RecordingImaging()
	# when / then
	with pytest.raises(DevicePreviewError) as exc:
		imaging.render_jpeg(f"/fake/{name}", 320, 5.0)
	assert exc.value.kind is DevicePreviewErrorKind.NO_PREVIEW
	assert imaging.calls == []


def _jpeg_with_orientation(orientation: int) -> bytes:
	ifd = b"\x00\x01\x01\x12\x00\x03\x00\x00\x00\x01" + orientation.to_bytes(2, "big") + b"\x00\x00\x00\x00\x00\x00"
	body = b"Exif\x00\x00MM\x00*\x00\x00\x00\x08" + ifd
	return b"\xff\xd8\xff\xe1" + (len(body) + 2).to_bytes(2, "big") + body + b"\xff\xd9"


def test_given_preview_without_exif_when_render_embedded_then_fallback_orient_before_input_and_never_enlarges() -> None:
	# given
	imaging = _RecordingImaging()
	# when
	imaging.render_embedded_jpeg(b"\xff\xd8\xff\xd9", 1600, 6, 5.0)
	# then
	args = imaging.calls[0]
	assert args[args.index("-orient") + 1] == "RightTop"
	assert args.index("-orient") < args.index("jpeg:-")
	assert "-auto-orient" in args
	assert "1600x1600>" in args
	assert "-strip" in args


def test_given_preview_with_own_orientation_when_render_embedded_then_fallback_is_ignored() -> None:
	# given
	imaging = _RecordingImaging()
	# when
	imaging.render_embedded_jpeg(_jpeg_with_orientation(6), 320, 8, 5.0)
	# then
	args = imaging.calls[0]
	assert "-orient" not in args
	assert "-auto-orient" in args


def test_given_fallback_one_when_render_embedded_then_no_orient_flag() -> None:
	# given
	imaging = _RecordingImaging()
	# when
	imaging.render_embedded_jpeg(b"\xff\xd8\xff\xd9", 320, 1, 5.0)
	# then
	assert "-orient" not in imaging.calls[0]


@pytest.mark.parametrize(
	("orientation", "name"),
	[
		(2, "TopRight"),
		(3, "BottomRight"),
		(4, "BottomLeft"),
		(5, "LeftTop"),
		(6, "RightTop"),
		(7, "RightBottom"),
		(8, "LeftBottom"),
	],
)
def test_given_fallback_orientation_when_render_embedded_then_magick_orientation_name(
	orientation: int, name: str
) -> None:
	# given
	imaging = _RecordingImaging()
	# when
	imaging.render_embedded_jpeg(b"\xff\xd8\xff\xd9", 320, orientation, 5.0)
	# then
	args = imaging.calls[0]
	assert args[args.index("-orient") + 1] == name


def test_given_magick_times_out_when_render_embedded_then_timeout_error() -> None:
	# given
	class _Slow(SubprocessPreviewImaging):
		def _run_magick(self, args: list[str], stdin: bytes | None, timeout_s: float) -> bytes:
			raise subprocess.TimeoutExpired("magick", timeout_s)

	# when / then
	with pytest.raises(DevicePreviewError) as exc:
		_Slow().render_embedded_jpeg(b"\xff\xd8", 320, 1, 1.0)
	assert exc.value.kind is DevicePreviewErrorKind.TIMEOUT


def test_given_magick_fails_when_render_embedded_then_no_preview() -> None:
	# given
	class _Broken(SubprocessPreviewImaging):
		def _run_magick(self, args: list[str], stdin: bytes | None, timeout_s: float) -> bytes:
			raise subprocess.CalledProcessError(1, "magick")

	# when / then
	with pytest.raises(DevicePreviewError) as exc:
		_Broken().render_embedded_jpeg(b"\xff\xd8", 320, 1, 1.0)
	assert exc.value.kind is DevicePreviewErrorKind.NO_PREVIEW
