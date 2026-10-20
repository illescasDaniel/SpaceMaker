from __future__ import annotations

import re
import subprocess
import threading
import time

from spacemaker.adapters.outbound.media.tool_runner import ToolRunner
from spacemaker.bootstrap.bundled_tools import BundledTool
from spacemaker.domain.device_preview import DevicePreviewError, DevicePreviewErrorKind, VideoPoster


_popen = subprocess.Popen  # seam: tests inject a fake process
_FORMAT_WHITELIST = "mov,mp4,m4a,3gp,3g2,mj2,matroska,webm"  # the demuxers of PREVIEWABLE_VIDEO_EXTENSIONS only
_JPEG_QUALITY = "4"  # ffmpeg mjpeg -q:v scale (2 best .. 31 worst)
_POLL_INTERVAL_S = 0.2
_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d{2}):(\d{2}(?:\.\d+)?)")
_HTTP_STATUS_RE = re.compile(r"(?:Server returned|HTTP error)\s+(409|503)\b")
_STDERR_DETAIL_CHARS = 300


def _parse_duration(stderr: str) -> float | None:
	match = _DURATION_RE.search(stderr)
	if match is None:
		return None
	hours, minutes, seconds = match.groups()
	return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _run_ffmpeg(argv: list[str], timeout_s: float, cancel: threading.Event | None) -> tuple[int, bytes, str]:
	"""Run ``argv``; returns ``(returncode, stdout, stderr_text)``.

	Raises ``subprocess.TimeoutExpired`` after ``timeout_s`` or when ``cancel`` is set (the process is killed
	first). ``OSError`` propagates when the binary cannot start.
	"""
	deadline = time.monotonic() + timeout_s
	with _popen(  # noqa: S603
		argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE
	) as process:
		while True:
			remaining = deadline - time.monotonic()
			if remaining <= 0 or (cancel is not None and cancel.is_set()):
				process.kill()
				process.communicate()
				raise subprocess.TimeoutExpired(argv, timeout_s)
			try:
				stdout, stderr = process.communicate(timeout=min(_POLL_INTERVAL_S, remaining))
			except subprocess.TimeoutExpired:
				continue
			return process.returncode, stdout, stderr.decode("utf-8", errors="replace")


class FfmpegVideoPoster:
	"""``VideoPosterPort`` backed by an ffmpeg subprocess reading the loopback stream URL.

	Untrusted media: only ``http``/``tcp`` may be opened (``-protocol_whitelist``) and only the MP4/MOV and
	Matroska/WebM demuxers may probe it (``-format_whitelist``, so a DASH/IMF manifest named ``.mp4`` cannot make
	ffmpeg fetch other URLs), exactly one input, one
	frame out as JPEG on stdout. ffmpeg applies the rotation metadata by default (autorotate), so portrait
	clips come out upright.
	"""

	def __init__(self, runner: ToolRunner | None = None) -> None:
		self._runner = runner or ToolRunner()

	def render_poster(
		self, source_url: str, max_edge: int, timeout_s: float, cancel: threading.Event | None = None
	) -> VideoPoster:
		try:
			ffmpeg = str(self._runner.path(BundledTool.FFMPEG))
		except FileNotFoundError as exc:
			raise DevicePreviewError(DevicePreviewErrorKind.NO_PREVIEW, "ffmpeg is not installed") from exc
		argv = [
			ffmpeg,
			"-hide_banner",
			"-nostdin",
			"-protocol_whitelist",
			"http,tcp",
			"-format_whitelist",
			_FORMAT_WHITELIST,
			"-i",
			source_url,
			"-frames:v",
			"1",
			"-an",
			"-sn",
			"-vf",
			f"scale={max_edge}:{max_edge}:force_original_aspect_ratio=decrease",
			"-f",
			"mjpeg",
			"-q:v",
			_JPEG_QUALITY,
			"pipe:1",
		]
		try:
			returncode, stdout, stderr = _run_ffmpeg(argv, timeout_s, cancel)
		except subprocess.TimeoutExpired as exc:
			raise DevicePreviewError(DevicePreviewErrorKind.TIMEOUT, "poster render timed out") from exc
		except OSError as exc:
			raise DevicePreviewError(DevicePreviewErrorKind.NO_PREVIEW, str(exc)) from exc
		if returncode != 0:
			status = _HTTP_STATUS_RE.search(stderr)
			if status is not None:
				kind = (
					DevicePreviewErrorKind.DEVICE_BUSY if status.group(1) == "409" else DevicePreviewErrorKind.UNPLUGGED
				)
				raise DevicePreviewError(kind)
			raise DevicePreviewError(DevicePreviewErrorKind.NO_PREVIEW, stderr.strip()[-_STDERR_DETAIL_CHARS:])
		if not stdout:
			raise DevicePreviewError(DevicePreviewErrorKind.NO_PREVIEW, "no video frame")
		return VideoPoster(stdout, _parse_duration(stderr))
