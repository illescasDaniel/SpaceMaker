from __future__ import annotations

from pathlib import Path

from spacemaker.adapters.outbound.media.tool_runner import ToolRunner
from spacemaker.bootstrap.bundled_tools import BundledTool
from spacemaker.domain.gallery_cache_paths import thumbnail_path
from spacemaker.domain.library import LibraryFolder
from spacemaker.domain.media import MediaKind, media_kind_for_filename


THUMB_SIZE = 320


class SubprocessThumbnailGenerator:
	def __init__(self, runner: ToolRunner | None = None) -> None:
		self._runner = runner or ToolRunner()

	def ensure_thumb(self, library_root: str, relative_path: str) -> str:
		source = Path(self._library_processed_path(library_root, relative_path))
		if not source.is_file():
			raise FileNotFoundError(relative_path)
		dest = Path(thumbnail_path(library_root, relative_path))
		dest.parent.mkdir(parents=True, exist_ok=True)
		if dest.is_file() and dest.stat().st_mtime >= source.stat().st_mtime:
			return str(dest)
		kind = media_kind_for_filename(relative_path)
		if kind is MediaKind.VIDEO:
			self._thumb_video(source, dest)
		else:
			self._thumb_image(source, dest)
		return str(dest)

	def _library_processed_path(self, library_root: str, relative: str) -> str:
		base = Path(library_root) / LibraryFolder.PROCESSED.value
		return str((base / relative).resolve())

	def _thumb_image(self, source: Path, dest: Path) -> None:
		# Fit within THUMB_SIZE×THUMB_SIZE; keep source aspect (no ^ cover / -extent crop).
		size = str(THUMB_SIZE)
		self._runner.run(
			BundledTool.MAGICK,
			[
				str(source),
				"-thumbnail",
				f"{size}x{size}",
				str(dest),
			],
			check=True,
		)

	def _thumb_video(self, source: Path, dest: Path) -> None:
		# First frame, fit-within max edge (same intent as image thumbs).
		scale = f"scale={THUMB_SIZE}:{THUMB_SIZE}:force_original_aspect_ratio=decrease"
		self._runner.run(
			BundledTool.FFMPEG,
			[
				"-y",
				"-i",
				str(source),
				"-frames:v",
				"1",
				"-vf",
				scale,
				"-q:v",
				"3",
				str(dest),
			],
			check=True,
		)
