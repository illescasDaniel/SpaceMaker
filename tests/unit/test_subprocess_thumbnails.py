from __future__ import annotations

from pathlib import Path
from typing import cast

from spacemaker.adapters.outbound.media.subprocess_thumbnails import (
	THUMB_SIZE,
	SubprocessThumbnailGenerator,
)
from spacemaker.adapters.outbound.media.tool_runner import ToolRunner
from spacemaker.bootstrap.bundled_tools import BundledTool
from spacemaker.domain.library import LibraryFolder


class _RecordingRunner:
	def __init__(self) -> None:
		self.calls: list[tuple[BundledTool, list[str]]] = []

	def run(
		self,
		tool: BundledTool,
		args: list[str],
		*,
		check: bool = True,
	) -> None:
		del check
		self.calls.append((tool, list(args)))


def _processed_source(library: Path, relative: str) -> Path:
	path = library / LibraryFolder.PROCESSED.value / relative
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_bytes(b"source")
	return path


def test_given_image_when_ensure_thumb_then_magick_fit_within_preserves_aspect(
	tmp_path: Path,
) -> None:
	# given
	library = tmp_path / "library"
	relative = "2025/photo.avif"
	_processed_source(library, relative)
	runner = _RecordingRunner()
	thumbs = SubprocessThumbnailGenerator(cast(ToolRunner, runner))

	# when
	thumbs.ensure_thumb(str(library), relative)

	# then
	assert len(runner.calls) == 1
	tool, args = runner.calls[0]
	assert tool is BundledTool.MAGICK
	assert "-thumbnail" in args
	geometry = args[args.index("-thumbnail") + 1]
	assert geometry == f"{THUMB_SIZE}x{THUMB_SIZE}"
	assert not geometry.endswith("^")
	assert "-extent" not in args
	assert "-gravity" not in args


def test_given_video_when_ensure_thumb_then_ffmpeg_scales_fit_within(
	tmp_path: Path,
) -> None:
	# given
	library = tmp_path / "library"
	relative = "2025/clip.av1.mp4"
	_processed_source(library, relative)
	runner = _RecordingRunner()
	thumbs = SubprocessThumbnailGenerator(cast(ToolRunner, runner))

	# when
	thumbs.ensure_thumb(str(library), relative)

	# then
	assert len(runner.calls) == 1
	tool, args = runner.calls[0]
	assert tool is BundledTool.FFMPEG
	assert "-vf" in args
	scale = args[args.index("-vf") + 1]
	assert scale == f"scale={THUMB_SIZE}:{THUMB_SIZE}:force_original_aspect_ratio=decrease"
