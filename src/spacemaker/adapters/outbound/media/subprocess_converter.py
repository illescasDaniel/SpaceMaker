from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from pathlib import Path

from spacemaker.adapters.outbound.media.tool_runner import ToolExecutionError, ToolRunner
from spacemaker.bootstrap.bundled_tools import BundledTool


class SubprocessMediaConverter:
	def __init__(self, runner: ToolRunner | None = None) -> None:
		self._runner = runner or ToolRunner()

	def encode_image_to_avif(self, source: str, destination: str) -> None:
		source_path = str(Path(source).resolve())
		dest_path = str(Path(destination).resolve())
		Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
		self._runner.run(
			BundledTool.MAGICK,
			[
				source_path,
				"-depth",
				"10",
				"-quality",
				"80",
				"-define",
				"avif:chroma-subsampling=444",
				dest_path,
			],
		)
		try:
			self._runner.run(
				BundledTool.EXIFTOOL,
				["-overwrite_original", "-TagsFromFile", source_path, "-all:all", dest_path],
				check=False,
			)
		except FileNotFoundError:
			pass

	def encode_video_to_av1(self, source: str, destination: str) -> None:
		source_path = str(Path(source).resolve())
		dest_path = str(Path(destination).resolve())
		Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
		encoder = self._pick_video_encoder()
		args = ["-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i", source_path]
		args.extend(encoder)
		args.extend(
			[
				"-c:a",
				"libopus",
				"-b:a",
				"256k",
				"-map_metadata",
				"0",
				"-movflags",
				"+faststart",
				dest_path,
			]
		)
		self._runner.run(BundledTool.FFMPEG, args)

	def encode_image_to_jpeg(self, source: str, destination: str) -> None:
		source_path = str(Path(source).resolve())
		dest_path = str(Path(destination).resolve())
		Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
		self._runner.run(
			BundledTool.MAGICK,
			[source_path, "-quality", "95", dest_path],
		)
		try:
			self._runner.run(
				BundledTool.EXIFTOOL,
				["-overwrite_original", "-TagsFromFile", source_path, "-all:all", dest_path],
				check=False,
			)
		except FileNotFoundError:
			pass

	def encode_video_to_h264_aac(
		self,
		source: str,
		destination: str,
		*,
		on_progress: Callable[[int], None] | None = None,
	) -> None:
		source_path = str(Path(source).resolve())
		dest_path = str(Path(destination).resolve())
		Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
		duration_ms = self._video_duration_ms(source_path)
		args = [
			"-nostdin",
			"-hide_banner",
			"-loglevel",
			"error",
			"-y",
			"-progress",
			"pipe:1",
			"-i",
			source_path,
			"-c:v",
			"libx264",
			"-crf",
			"18",
			"-pix_fmt",
			"yuv420p",
			"-c:a",
			"aac",
			"-b:a",
			"256k",
			"-map_metadata",
			"0",
			"-movflags",
			"+faststart",
			dest_path,
		]
		cmd = [str(self._runner.path(BundledTool.FFMPEG)), *args]
		if on_progress:
			on_progress(10)
		proc = subprocess.Popen(  # noqa: S603
			cmd,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			text=True,
		)
		last_percent = 10
		if proc.stdout is not None:
			for line in proc.stdout:
				line = line.strip()
				if not line.startswith("out_time_ms="):
					continue
				if duration_ms <= 0:
					continue
				match = re.search(r"out_time_ms=(\d+)", line)
				if not match:
					continue
				out_ms = int(match.group(1))
				percent = min(99, max(last_percent, int((out_ms / duration_ms) * 100)))
				if percent > last_percent and on_progress is not None:
					last_percent = percent
					on_progress(percent)
		stderr = proc.stderr.read() if proc.stderr is not None else ""
		proc.wait()
		if proc.returncode != 0:
			result = subprocess.CompletedProcess(cmd, proc.returncode, "", stderr)
			raise ToolExecutionError(BundledTool.FFMPEG, cmd, result)
		if on_progress:
			on_progress(100)

	def _video_duration_ms(self, source_path: str) -> int:
		try:
			result = self._runner.run(
				BundledTool.FFPROBE,
				[
					"-v",
					"error",
					"-show_entries",
					"format=duration",
					"-of",
					"default=noprint_wrappers=1:nokey=1",
					source_path,
				],
				check=False,
			)
		except FileNotFoundError:
			return 0
		if result.returncode != 0:
			return 0
		text = result.stdout.strip()
		try:
			seconds = float(text)
		except ValueError:
			return 0
		if seconds <= 0:
			return 0
		return int(seconds * 1000)

	def _pick_video_encoder(self) -> list[str]:
		try:
			result = self._runner.run(BundledTool.FFMPEG, ["-encoders"], check=False)
		except FileNotFoundError:
			return ["-c:v", "libsvtav1", "-crf", "23", "-preset", "5", "-pix_fmt", "yuv420p10le"]
		text = result.stdout + result.stderr
		if "av1_nvenc" in text:
			return ["-c:v", "av1_nvenc", "-preset", "p6", "-cq", "24", "-pix_fmt", "p010le"]
		if "av1_qsv" in text:
			return ["-c:v", "av1_qsv", "-global_quality", "24", "-preset", "medium", "-pix_fmt", "p010le"]
		if "av1_vaapi" in text:
			return ["-vf", "format=p010,hwupload", "-c:v", "av1_vaapi", "-rc_mode", "CQP", "-qp", "24"]
		return ["-c:v", "libsvtav1", "-crf", "23", "-preset", "5", "-pix_fmt", "yuv420p10le"]
