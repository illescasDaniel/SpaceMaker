from __future__ import annotations

import re
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from spacemaker.adapters.outbound.media.ffmpeg_encoders import (
	av1_encoder_ffmpeg_args,
	h264_hw_encoder_ffmpeg_args,
	hardware_video_encoder_from_ffmpeg_encoders,
)
from spacemaker.adapters.outbound.media.raw_preview import extract_raw_embedded_jpeg
from spacemaker.adapters.outbound.media.tool_runner import ToolExecutionError, ToolRunner
from spacemaker.bootstrap.bundled_tools import BundledTool
from spacemaker.domain.media import is_raw_extension, normalize_extension
from spacemaker.domain.video_encode import HardwareVideoEncoder


class SubprocessMediaConverter:
	def __init__(self, runner: ToolRunner | None = None) -> None:
		self._runner = runner or ToolRunner()
		self._encoder_text: str | None = None
		self._library_encoder: HardwareVideoEncoder | None = None

	def encode_image_to_avif(self, source: str, destination: str) -> None:
		source_path = Path(source).resolve()
		dest_path = str(Path(destination).resolve())
		Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
		try:
			self._magick_encode_avif(str(source_path), dest_path)
		except ToolExecutionError:
			ext = normalize_extension(source_path.name)
			if not is_raw_extension(ext):
				raise
			with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
				preview_path = Path(tmp.name)
			try:
				exiftool = self._runner.path(BundledTool.EXIFTOOL)
				if not extract_raw_embedded_jpeg(
					source=source_path,
					destination=preview_path,
					exiftool=exiftool,
				):
					raise ToolExecutionError(
						BundledTool.MAGICK,
						["magick", str(source_path)],
						subprocess.CompletedProcess([], 1, "", "no embedded RAW preview"),
					)
				self._magick_encode_avif(str(preview_path), dest_path)
			finally:
				preview_path.unlink(missing_ok=True)
		self._copy_image_metadata(source_path, dest_path)

	def _magick_encode_avif(self, source_path: str, dest_path: str) -> None:
		self._runner.run(
			BundledTool.MAGICK,
			[
				source_path,
				"-auto-orient",
				"-depth",
				"10",
				"-quality",
				"80",
				"-define",
				"avif:chroma-subsampling=444",
				dest_path,
			],
		)

	def _copy_image_metadata(self, source_path: Path, dest_path: str) -> None:
		try:
			self._runner.run(
				BundledTool.EXIFTOOL,
				[
					"-overwrite_original",
					"-TagsFromFile",
					str(source_path),
					"-all:all",
					"--Orientation:all",
					dest_path,
				],
				check=False,
			)
		except FileNotFoundError:
			pass

	def library_video_encoder(self) -> HardwareVideoEncoder:
		if self._library_encoder is None:
			text = self._ffmpeg_encoders_text()
			self._library_encoder = hardware_video_encoder_from_ffmpeg_encoders(
				text,
				vaapi_render_node=self._vaapi_render_node_available(),
			)
		return self._library_encoder

	def encode_video_to_av1(self, source: str, destination: str) -> None:
		source_path = str(Path(source).resolve())
		dest_path = str(Path(destination).resolve())
		Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
		encoder = av1_encoder_ffmpeg_args(
			self._ffmpeg_encoders_text(),
			vaapi_render_node=self._vaapi_render_node_available(),
		)
		if encoder is None:
			raise RuntimeError("no hardware AV1 encoder available")
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
		source_path = Path(source).resolve()
		dest_path = str(Path(destination).resolve())
		Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
		self._runner.run(
			BundledTool.MAGICK,
			[str(source_path), "-auto-orient", "-quality", "95", dest_path],
		)
		self._copy_image_metadata(source_path, dest_path)

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
		video_encoder = h264_hw_encoder_ffmpeg_args(
			self._ffmpeg_encoders_text(),
			vaapi_render_node=self._vaapi_render_node_available(),
		)
		if video_encoder is None:
			raise RuntimeError("no hardware H.264 encoder available")
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
			*video_encoder,
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

	def _ffmpeg_encoders_text(self) -> str:
		if self._encoder_text is not None:
			return self._encoder_text
		try:
			result = self._runner.run(BundledTool.FFMPEG, ["-encoders"], check=False)
		except FileNotFoundError:
			self._encoder_text = ""
		else:
			self._encoder_text = result.stdout + result.stderr
		return self._encoder_text

	def _vaapi_render_node_available(self) -> bool:
		return Path("/dev/dri/renderD128").exists()
