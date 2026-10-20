from __future__ import annotations

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
	imaging.render_jpeg(f"/tmp/{name}", 320, 5.0)
	# then
	assert f"{prefix}/tmp/{name}[0]" in imaging.calls[0]


@pytest.mark.parametrize("name", ["a.svg", "a.mvg", "a", "a.txt"])
def test_given_unknown_extension_when_render_jpeg_then_no_preview_without_spawning(name: str) -> None:
	# given
	imaging = _RecordingImaging()
	# when / then
	with pytest.raises(DevicePreviewError) as exc:
		imaging.render_jpeg(f"/tmp/{name}", 320, 5.0)
	assert exc.value.kind is DevicePreviewErrorKind.NO_PREVIEW
	assert imaging.calls == []
