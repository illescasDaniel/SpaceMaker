from __future__ import annotations

import json
import re
from pathlib import Path

from spacemaker.adapters.outbound.media.tool_runner import ToolRunner
from spacemaker.bootstrap.bundled_tools import BundledTool
from spacemaker.domain.web_compat import VideoProbe


class SubprocessMediaProbe:
	def __init__(self, runner: ToolRunner | None = None) -> None:
		self._runner = runner or ToolRunner()

	def probe_video(self, path: str) -> VideoProbe | None:
		source = str(Path(path).resolve())
		try:
			result = self._runner.run(
				BundledTool.FFPROBE,
				[
					"-v",
					"error",
					"-show_entries",
					"format=bit_rate,duration:stream=codec_name",
					"-of",
					"json",
					source,
				],
				check=False,
			)
		except FileNotFoundError:
			return None
		if result.returncode != 0:
			return None
		try:
			data = json.loads(result.stdout)
		except json.JSONDecodeError:
			return None
		streams = data.get("streams") or []
		video_codec = ""
		audio_codec: str | None = None
		for stream in streams:
			name = (stream.get("codec_name") or "").lower()
			if name in {"h264", "hevc", "vp9", "av1", "mpeg4"} and not video_codec:
				video_codec = name
			elif name in {"aac", "mp3", "opus", "vorbis", "flac"} and audio_codec is None:
				audio_codec = name
		if not video_codec:
			return None
		fmt = data.get("format") or {}
		bitrate = int(fmt.get("bit_rate") or 0)
		if bitrate <= 0:
			duration = float(fmt.get("duration") or 0)
			if duration > 0:
				size = Path(source).stat().st_size
				bitrate = int((size * 8) / duration)
		ext = source.rsplit(".", 1)[-1].lower()
		return VideoProbe(container_ext=ext, video_codec=video_codec, audio_codec=audio_codec, bitrate_bps=bitrate)

	def image_readable(self, path: str) -> bool:
		return self.output_valid_image(path)

	def output_valid_image(self, path: str) -> bool:
		source = str(Path(path).resolve())
		try:
			result = self._runner.run(
				BundledTool.MAGICK,
				["identify", "-ping", source],
				check=False,
			)
		except FileNotFoundError:
			return False
		return result.returncode == 0

	def output_valid_video(self, path: str) -> bool:
		source = str(Path(path).resolve())
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
					source,
				],
				check=False,
			)
		except FileNotFoundError:
			return False
		if result.returncode != 0:
			return False
		text = result.stdout.strip()
		return bool(text and re.match(r"^[0-9.]+$", text))
