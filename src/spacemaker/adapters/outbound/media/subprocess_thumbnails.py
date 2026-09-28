from __future__ import annotations

import logging
import os
from pathlib import Path

from spacemaker.adapters.outbound.media.tool_runner import ToolRunner
from spacemaker.bootstrap.bundled_tools import BundledTool
from spacemaker.domain.gallery_cache_paths import thumbnail_path
from spacemaker.domain.library import LibraryFolder
from spacemaker.domain.media import MediaKind, media_kind_for_filename


logger = logging.getLogger(__name__)


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
		tmp = dest.with_name(dest.name + ".tmp.jpg")
		kind = media_kind_for_filename(relative_path)
		try:
			if kind is MediaKind.VIDEO:
				self._thumb_video(source, tmp)
			else:
				self._thumb_image(source, tmp)
			os.replace(tmp, dest)
		except (OSError, RuntimeError):
			logger.exception("thumbnail generation failed for %s", relative_path)
			tmp.unlink(missing_ok=True)
			raise
		return str(dest)

	def _library_processed_path(self, library_root: str, relative: str) -> str:
		base = Path(library_root) / LibraryFolder.PROCESSED.value
		return str((base / relative).resolve())

	def _thumb_image(self, source: Path, dest: Path) -> None:
		size = str(THUMB_SIZE)
		self._runner.run(
			BundledTool.MAGICK,
			[
				str(source),
				"-thumbnail",
				f"{size}x{size}>",
				str(dest),
			],
			check=True,
		)

	def _thumb_video(self, source: Path, dest: Path) -> None:
		size = str(THUMB_SIZE)
		self._runner.run(
			BundledTool.FFMPEG,
			[
				"-y",
				"-i",
				str(source),
				"-frames:v",
				"1",
				"-vf",
				f"scale='min({size},iw)':'min({size},ih)':force_original_aspect_ratio=decrease",
				"-q:v",
				"3",
				str(dest),
			],
			check=True,
		)
