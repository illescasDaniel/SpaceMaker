from __future__ import annotations

from pathlib import Path

from spacemaker.adapters.outbound.media.tool_runner import ToolRunner
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
