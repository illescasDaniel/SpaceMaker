# Video posters, FfmpegVideoPoster (SPEC "Video posters — strategy / trust boundary / failure handling").
# Seam Phase 4 must implement: module-level function in
# ``spacemaker.adapters.outbound.media.ffmpeg_video_poster``:
#     _run_ffmpeg(argv: list[str], timeout_s: float, cancel: threading.Event | None) -> tuple[int, bytes, str]
# returning (returncode, stdout_bytes, stderr_text); it raises ``subprocess.TimeoutExpired`` on timeout.
# ``FfmpegVideoPoster()`` takes no arguments and always calls ``_run_ffmpeg`` (JPEG on stdout, ``pipe:1``).
#   argv: ``-protocol_whitelist http,tcp``; the URL is the only ``-i`` input; ``-frames:v 1``;
#   ``-vf scale=<edge>:<edge>:force_original_aspect_ratio=decrease``; ``-f mjpeg``; output ``pipe:1``.
#   duration from stderr ``Duration: HH:MM:SS.xx`` -> seconds, missing / N/A -> None;
#   409 / 503 in stderr -> DEVICE_BUSY / UNPLUGGED; TimeoutExpired -> TIMEOUT; nonzero otherwise or empty
#   output -> NO_PREVIEW.
import subprocess
import threading

import pytest

from spacemaker.adapters.outbound.media import ffmpeg_video_poster
from spacemaker.adapters.outbound.media.ffmpeg_video_poster import FfmpegVideoPoster
from spacemaker.domain.device_preview import DevicePreviewError, DevicePreviewErrorKind, VideoPoster


URL = "http://127.0.0.1:8123/api/device/stream?token=abc_DEF-123"
JPEG = b"\xff\xd8\xff-poster"
STDERR_OK = (
	"Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'http://127.0.0.1:8123/api/device/stream?token=abc':\n"
	"  Duration: 00:00:42.37, start: 0.000000, bitrate: 47000 kb/s\n"
	"    Stream #0:0: Video: hevc, 3840x2160\n"
)


class _FakeFfmpeg:
	def __init__(
		self, returncode: int = 0, stdout: bytes = JPEG, stderr: str = STDERR_OK, timeout: bool = False
	) -> None:
		self.returncode = returncode
		self.stdout = stdout
		self.stderr = stderr
		self.timeout = timeout
		self.calls: list[tuple[list[str], float, threading.Event | None]] = []

	def __call__(self, argv: list[str], timeout_s: float, cancel: threading.Event | None) -> tuple[int, bytes, str]:
		self.calls.append((argv, timeout_s, cancel))
		if self.timeout:
			raise subprocess.TimeoutExpired(argv, timeout_s)
		return self.returncode, self.stdout, self.stderr


def _poster(monkeypatch: pytest.MonkeyPatch, fake: _FakeFfmpeg) -> FfmpegVideoPoster:
	monkeypatch.setattr(ffmpeg_video_poster, "_run_ffmpeg", fake)
	return FfmpegVideoPoster()


def _value_after(argv: list[str], flag: str) -> str:
	return argv[argv.index(flag) + 1]


def test_given_stream_url_when_render_poster_then_jpeg_and_duration_returned(monkeypatch: pytest.MonkeyPatch) -> None:
	# given
	poster = _poster(monkeypatch, _FakeFfmpeg())
	# when
	result = poster.render_poster(URL, 320, 20.0)
	# then
	assert result == VideoPoster(JPEG, 42.37)


def test_given_stream_url_when_render_poster_then_whitelisted_single_url_input_one_frame_jpeg_to_stdout(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	# given
	fake = _FakeFfmpeg()
	poster = _poster(monkeypatch, fake)
	# when
	poster.render_poster(URL, 320, 20.0)
	# then
	argv = fake.calls[0][0]
	assert _value_after(argv, "-protocol_whitelist") == "http,tcp"
	assert argv.count("-i") == 1
	assert _value_after(argv, "-i") == URL
	assert argv.index("-protocol_whitelist") < argv.index("-i")
	assert _value_after(argv, "-format_whitelist") == "mov,mp4,m4a,3gp,3g2,mj2,matroska,webm"
	assert argv.index("-format_whitelist") < argv.index("-i")
	assert _value_after(argv, "-frames:v") == "1"
	assert _value_after(argv, "-f") == "mjpeg"
	assert argv[-1] == "pipe:1"
	assert [arg for arg in argv if arg.startswith(("http:", "https:", "file:", "concat:"))] == [URL]


@pytest.mark.parametrize("edge", [320, 1600])
def test_given_max_edge_when_render_poster_then_fit_within_scale_filter(
	monkeypatch: pytest.MonkeyPatch, edge: int
) -> None:
	# given
	fake = _FakeFfmpeg()
	poster = _poster(monkeypatch, fake)
	# when
	poster.render_poster(URL, edge, 20.0)
	# then
	assert f"scale={edge}:{edge}:force_original_aspect_ratio=decrease" in _value_after(fake.calls[0][0], "-vf")


def test_given_timeout_and_cancel_when_render_poster_then_both_passed_to_runner(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	# given
	fake = _FakeFfmpeg()
	poster = _poster(monkeypatch, fake)
	cancel = threading.Event()
	# when
	poster.render_poster(URL, 320, 20.0, cancel)
	# then
	assert fake.calls[0][1:] == (20.0, cancel)


@pytest.mark.parametrize(
	("duration_line", "seconds"),
	[
		("Duration: 00:00:42.37, start: 0.0", 42.37),
		("Duration: 00:12:07.00, start: 0.0", 727.0),
		("Duration: 01:02:15.50, start: 0.0", 3735.5),
	],
)
def test_given_duration_line_when_render_poster_then_seconds_parsed(
	monkeypatch: pytest.MonkeyPatch, duration_line: str, seconds: float
) -> None:
	# given
	poster = _poster(monkeypatch, _FakeFfmpeg(stderr=f"Input #0, matroska:\n  {duration_line}\n"))
	# when
	result = poster.render_poster(URL, 320, 20.0)
	# then
	assert result.duration_s == pytest.approx(seconds)


@pytest.mark.parametrize(
	"stderr", ["Input #0, mp4:\n  Stream #0:0: Video: h264\n", "  Duration: N/A, bitrate: N/A\n", ""]
)
def test_given_no_usable_duration_when_render_poster_then_duration_none_but_jpeg_kept(
	monkeypatch: pytest.MonkeyPatch, stderr: str
) -> None:
	# given
	poster = _poster(monkeypatch, _FakeFfmpeg(stderr=stderr))
	# when
	result = poster.render_poster(URL, 320, 20.0)
	# then
	assert result == VideoPoster(JPEG, None)


@pytest.mark.parametrize(
	("stderr", "kind"),
	[
		("[http @ 0x1] HTTP error 409 Conflict\nServer returned 409 Conflict", DevicePreviewErrorKind.DEVICE_BUSY),
		("[http @ 0x1] Server returned 503 Service Unavailable", DevicePreviewErrorKind.UNPLUGGED),
		("Invalid data found when processing input", DevicePreviewErrorKind.NO_PREVIEW),
		("Output file does not contain any stream", DevicePreviewErrorKind.NO_PREVIEW),
	],
)
def test_given_ffmpeg_fails_when_render_poster_then_error_kind_from_stderr(
	monkeypatch: pytest.MonkeyPatch, stderr: str, kind: DevicePreviewErrorKind
) -> None:
	# given
	poster = _poster(monkeypatch, _FakeFfmpeg(returncode=1, stdout=b"", stderr=stderr))
	# when / then
	with pytest.raises(DevicePreviewError) as raised:
		poster.render_poster(URL, 320, 20.0)
	assert raised.value.kind is kind


def test_given_clean_exit_but_no_frame_when_render_poster_then_no_preview(monkeypatch: pytest.MonkeyPatch) -> None:
	# given (audio-only file: ffmpeg exits 0 with empty stdout)
	poster = _poster(monkeypatch, _FakeFfmpeg(returncode=0, stdout=b""))
	# when / then
	with pytest.raises(DevicePreviewError) as raised:
		poster.render_poster(URL, 320, 20.0)
	assert raised.value.kind is DevicePreviewErrorKind.NO_PREVIEW


def test_given_timeout_when_render_poster_then_timeout_error(monkeypatch: pytest.MonkeyPatch) -> None:
	# given
	poster = _poster(monkeypatch, _FakeFfmpeg(timeout=True))
	# when / then
	with pytest.raises(DevicePreviewError) as raised:
		poster.render_poster(URL, 320, 20.0)
	assert raised.value.kind is DevicePreviewErrorKind.TIMEOUT


def test_given_default_rotation_when_render_poster_then_autorotate_not_disabled(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	# given
	fake = _FakeFfmpeg()
	poster = _poster(monkeypatch, fake)
	# when
	poster.render_poster(URL, 320, 20.0)
	# then
	assert "-noautorotate" not in fake.calls[0][0]


class _FakeProcess:
	"""``subprocess.Popen`` stand-in: ``communicate`` times out until the process is killed."""

	def __init__(self, hangs: bool) -> None:
		self.hangs = hangs
		self.killed = False
		self.returncode = 0

	def __enter__(self) -> "_FakeProcess":
		return self

	def __exit__(self, *_exc: object) -> None:
		return None

	def kill(self) -> None:
		self.killed = True

	def communicate(self, timeout: float | None = None) -> tuple[bytes, bytes]:
		if self.hangs and not self.killed:
			raise subprocess.TimeoutExpired("ffmpeg", timeout or 0)
		return JPEG, b""


def _rig_process(monkeypatch: pytest.MonkeyPatch, hangs: bool) -> _FakeProcess:
	process = _FakeProcess(hangs)
	monkeypatch.setattr(ffmpeg_video_poster, "_popen", lambda *_args, **_kwargs: process)
	return process


def test_given_cancel_set_when_run_ffmpeg_then_process_killed_and_timeout_raised(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	# given
	process = _rig_process(monkeypatch, hangs=True)
	cancel = threading.Event()
	cancel.set()
	# when
	with pytest.raises(subprocess.TimeoutExpired):
		ffmpeg_video_poster._run_ffmpeg(["ffmpeg"], 20.0, cancel)
	# then
	assert process.killed


def test_given_deadline_passed_when_run_ffmpeg_then_process_killed_and_timeout_raised(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	# given
	process = _rig_process(monkeypatch, hangs=True)
	# when
	with pytest.raises(subprocess.TimeoutExpired):
		ffmpeg_video_poster._run_ffmpeg(["ffmpeg"], 0.0, None)
	# then
	assert process.killed


def test_given_process_finishes_when_run_ffmpeg_then_output_returned_and_not_killed(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	# given
	process = _rig_process(monkeypatch, hangs=False)
	# when
	returncode, stdout, stderr = ffmpeg_video_poster._run_ffmpeg(["ffmpeg"], 20.0, threading.Event())
	# then
	assert (returncode, stdout, stderr) == (0, JPEG, "")
	assert not process.killed
