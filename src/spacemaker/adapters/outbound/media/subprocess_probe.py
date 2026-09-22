from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from spacemaker.adapters.outbound.media.tool_runner import ToolRunner
from spacemaker.bootstrap.bundled_tools import BundledTool
from spacemaker.domain.gallery_metadata import GalleryDisplayMetadata
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

	def captured_at(self, path: str) -> datetime | None:
		source = str(Path(path).resolve())
		try:
			result = self._runner.run(
				BundledTool.EXIFTOOL,
				["-DateTimeOriginal", "-s", "-s", "-s", source],
				check=False,
			)
		except FileNotFoundError:
			return None
		if result.returncode != 0:
			return None
		text = result.stdout.strip()
		if not text:
			return None
		for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
			try:
				return datetime.strptime(text, fmt)
			except ValueError:
				continue
		return None

	def display_metadata(self, path: str) -> GalleryDisplayMetadata:
		source = str(Path(path).resolve())
		filename = Path(source).name
		stat = Path(source).stat()
		captured = self.captured_at(source)
		exif = self._exif_fields(source)
		make = (exif.get("Make") or "").strip()
		model = (exif.get("Model") or "").strip()
		gps = (exif.get("GPSPosition") or exif.get("GPSCoordinates") or "").strip()
		width: int | None = None
		height: int | None = None
		if exif.get("ImageWidth"):
			try:
				width = int(exif["ImageWidth"])
			except (TypeError, ValueError):
				width = None
		if exif.get("ImageHeight"):
			try:
				height = int(exif["ImageHeight"])
			except (TypeError, ValueError):
				height = None
		duration: float | None = None
		if self.probe_video(source) is not None:
			vdims = self._video_dimensions(source)
			if vdims:
				width, height = vdims
			duration = self._video_duration_seconds(source)
		return GalleryDisplayMetadata(
			filename=filename,
			captured_at=captured,
			camera_make=make,
			camera_model=model,
			width=width,
			height=height,
			duration_seconds=duration,
			file_size_bytes=stat.st_size,
			gps=gps,
		)

	def _exif_fields(self, source: str) -> dict[str, str]:
		try:
			result = self._runner.run(
				BundledTool.EXIFTOOL,
				[
					"-json",
					"-Make",
					"-Model",
					"-ImageWidth",
					"-ImageHeight",
					"-GPSPosition",
					"-GPSCoordinates",
					source,
				],
				check=False,
			)
		except FileNotFoundError:
			return {}
		if result.returncode != 0:
			return {}
		try:
			data = json.loads(result.stdout)
		except json.JSONDecodeError:
			return {}
		if not data or not isinstance(data, list):
			return {}
		block = data[0]
		if not isinstance(block, dict):
			return {}
		out: dict[str, str] = {}
		for key, value in block.items():
			if value is None:
				continue
			out[key] = str(value)
		return out

	def _video_dimensions(self, source: str) -> tuple[int, int] | None:
		try:
			result = self._runner.run(
				BundledTool.FFPROBE,
				[
					"-v",
					"error",
					"-select_streams",
					"v:0",
					"-show_entries",
					"stream=width,height",
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
		if not streams:
			return None
		stream = streams[0]
		try:
			w = int(stream.get("width") or 0)
			h = int(stream.get("height") or 0)
		except (TypeError, ValueError):
			return None
		if w <= 0 or h <= 0:
			return None
		return w, h

	def _video_duration_seconds(self, source: str) -> float | None:
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
			return None
		if result.returncode != 0:
			return None
		text = result.stdout.strip()
		try:
			value = float(text)
		except ValueError:
			return None
		return value if value > 0 else None
