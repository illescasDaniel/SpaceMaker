import logging
import subprocess
from pathlib import Path

import pytest

from spacemaker.adapters.outbound.media.subprocess_thumbnails import SubprocessThumbnailGenerator
from spacemaker.adapters.outbound.media.tool_runner import ToolExecutionError, ToolRunner
from spacemaker.bootstrap.bundled_tools import BundledTool
from spacemaker.domain.gallery_cache_paths import thumbnail_path
from spacemaker.domain.library import LibraryFolder


class FakeToolRunner(ToolRunner):
	"""Records invocations and either writes the requested destination or fails, without spawning a subprocess."""

	def __init__(self, *, fail: bool = False) -> None:
		self.calls: list[tuple[BundledTool, list[str]]] = []
		self._fail = fail

	def run(self, tool: BundledTool, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
		self.calls.append((tool, args))
		if self._fail:
			result = subprocess.CompletedProcess(args, returncode=1, stdout="", stderr="boom")
			if check:
				raise ToolExecutionError(tool, args, result)
			return result
		Path(args[-1]).write_bytes(b"thumb")
		return subprocess.CompletedProcess(args, returncode=0, stdout="", stderr="")


def _install_processed_file(library: Path, rel: str) -> None:
	source = library / LibraryFolder.PROCESSED.value / rel
	source.parent.mkdir(parents=True, exist_ok=True)
	source.write_bytes(b"avif-bytes")


def test_given_processed_image_when_ensure_thumb_then_writes_to_temp_then_renames(tmp_path: Path) -> None:
	# given
	library = tmp_path / "lib"
	rel = "photo.avif"
	_install_processed_file(library, rel)
	runner = FakeToolRunner()
	generator = SubprocessThumbnailGenerator(runner)
	dest = Path(thumbnail_path(str(library), rel))
	tmp = dest.with_name(dest.name + ".tmp.jpg")
	# when
	result = generator.ensure_thumb(str(library), rel)
	# then
	assert result == str(dest)
	assert dest.is_file()
	assert not tmp.exists()
	assert runner.calls[0][0] is BundledTool.MAGICK
	assert runner.calls[0][1][-1] == str(tmp)


def test_given_magick_fails_when_ensure_thumb_then_no_final_file_and_temp_cleaned_up(tmp_path: Path) -> None:
	# given
	library = tmp_path / "lib"
	rel = "photo.avif"
	_install_processed_file(library, rel)
	generator = SubprocessThumbnailGenerator(FakeToolRunner(fail=True))
	dest = Path(thumbnail_path(str(library), rel))
	tmp = dest.with_name(dest.name + ".tmp.jpg")
	# when / then
	with pytest.raises(RuntimeError):
		generator.ensure_thumb(str(library), rel)
	assert not dest.exists()
	assert not tmp.exists()


def test_given_magick_fails_when_ensure_thumb_then_logs_relative_path(tmp_path: Path, caplog) -> None:
	# given
	library = tmp_path / "lib"
	rel = "photo.avif"
	_install_processed_file(library, rel)
	generator = SubprocessThumbnailGenerator(FakeToolRunner(fail=True))
	# when
	with (
		caplog.at_level(logging.ERROR, logger="spacemaker.adapters.outbound.media.subprocess_thumbnails"),
		pytest.raises(RuntimeError),
	):
		generator.ensure_thumb(str(library), rel)
	# then
	assert any(rel in record.message for record in caplog.records)


def test_given_missing_processed_source_when_ensure_thumb_then_raises_file_not_found(tmp_path: Path) -> None:
	# given
	library = tmp_path / "lib"
	generator = SubprocessThumbnailGenerator(FakeToolRunner())
	# when / then
	with pytest.raises(FileNotFoundError):
		generator.ensure_thumb(str(library), "missing.avif")


def test_given_processed_image_when_ensure_thumb_then_magick_fits_within_bounds_without_cropping(
	tmp_path: Path,
) -> None:
	# given
	library = tmp_path / "lib"
	rel = "photo.avif"
	_install_processed_file(library, rel)
	runner = FakeToolRunner()
	generator = SubprocessThumbnailGenerator(runner)
	# when
	generator.ensure_thumb(str(library), rel)
	# then
	args = runner.calls[0][1]
	assert "-thumbnail" in args
	geometry = args[args.index("-thumbnail") + 1]
	assert geometry == "320x320>"
	assert "-extent" not in args
	assert "-gravity" not in args


def test_given_processed_video_when_ensure_thumb_then_ffmpeg_scales_preserving_aspect(tmp_path: Path) -> None:
	# given
	library = tmp_path / "lib"
	rel = "clip.av1.mp4"
	_install_processed_file(library, rel)
	runner = FakeToolRunner()
	generator = SubprocessThumbnailGenerator(runner)
	# when
	generator.ensure_thumb(str(library), rel)
	# then
	tool, args = runner.calls[0]
	assert tool is BundledTool.FFMPEG
	assert "-vf" in args
	scale_filter = args[args.index("-vf") + 1]
	assert "force_original_aspect_ratio=decrease" in scale_filter
	assert "-extent" not in args
