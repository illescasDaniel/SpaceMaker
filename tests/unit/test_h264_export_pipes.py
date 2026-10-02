from __future__ import annotations

import stat
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from spacemaker.adapters.outbound.media import subprocess_converter as module
from spacemaker.adapters.outbound.media.subprocess_converter import SubprocessMediaConverter
from spacemaker.adapters.outbound.media.tool_runner import ToolExecutionError


pytestmark = [
	pytest.mark.integration,
	pytest.mark.skipif(sys.platform == "win32", reason="uses a POSIX shell script as fake ffmpeg"),
]


def _converter_with_fake_ffmpeg(tmp_path: Path, monkeypatch, script_body: str) -> SubprocessMediaConverter:
	ffmpeg = tmp_path / "ffmpeg"
	ffmpeg.write_text("#!/bin/sh\n" + script_body, encoding="utf-8")
	ffmpeg.chmod(ffmpeg.stat().st_mode | stat.S_IXUSR)
	converter = SubprocessMediaConverter(runner=SimpleNamespace(path=lambda _tool: ffmpeg))  # type: ignore[arg-type]
	converter._video_duration_ms = lambda _src: 10_000  # type: ignore[method-assign]
	converter._ffmpeg_encoders_text = lambda: ""  # type: ignore[method-assign]
	converter._vaapi_render_node_available = lambda: False  # type: ignore[method-assign]
	monkeypatch.setattr(module, "h264_hw_encoder_ffmpeg_args", lambda *_a, **_k: ["-c:v", "fake"])
	return converter


def _run_with_timeout(fn, timeout: float = 20.0) -> BaseException | None:
	outcome: dict[str, BaseException | None] = {}

	def call() -> None:
		try:
			fn()
			outcome["error"] = None
		except BaseException as exc:
			outcome["error"] = exc

	worker = threading.Thread(target=call, daemon=True)
	worker.start()
	worker.join(timeout)
	assert not worker.is_alive(), "export hung (stderr/stdout pipe deadlock)"
	return outcome["error"]


def test_given_ffmpeg_writing_lots_of_stderr_when_h264_export_then_finishes_and_reports_progress(
	tmp_path: Path, monkeypatch
) -> None:
	# given: >1 MB on stderr before any progress line would fill a 64 KB pipe nobody drains.
	converter = _converter_with_fake_ffmpeg(
		tmp_path,
		monkeypatch,
		'head -c 1500000 /dev/zero | tr "\\0" "e" >&2\n'
		'echo "out_time_ms=5000000"\necho "out_time_ms=9000000"\n'
		'for last; do :; done\necho out > "$last"\n',
	)
	src = tmp_path / "in.mov"
	src.write_bytes(b"x")
	seen: list[int] = []
	# when
	error = _run_with_timeout(
		lambda: converter.encode_video_to_h264_aac(str(src), str(tmp_path / "out.mp4"), on_progress=seen.append)
	)
	# then
	assert error is None
	assert (tmp_path / "out.mp4").is_file()
	assert 50 in seen and seen[-1] == 100


def test_given_ffmpeg_failing_when_h264_export_then_error_carries_stderr_text(tmp_path: Path, monkeypatch) -> None:
	# given
	converter = _converter_with_fake_ffmpeg(tmp_path, monkeypatch, 'echo "codec exploded" >&2\nexit 3\n')
	src = tmp_path / "in.mov"
	src.write_bytes(b"x")
	# when
	error = _run_with_timeout(lambda: converter.encode_video_to_h264_aac(str(src), str(tmp_path / "out.mp4")))
	# then
	assert isinstance(error, ToolExecutionError)
	assert "codec exploded" in str(error)
