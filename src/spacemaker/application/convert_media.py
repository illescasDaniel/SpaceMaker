from __future__ import annotations

from collections.abc import Callable

from spacemaker.domain.conversion import (
	ConversionRoute,
	image_avif_relative_path,
	output_exceeds_rollback_threshold,
	route_before_encode,
	video_av1_relative_path,
)
from spacemaker.domain.library import JobProgress, LibraryFolder
from spacemaker.domain.media import MediaKind, media_kind_for_extension, normalize_extension
from spacemaker.domain.web_compat import VideoProbe, is_web_compatible_image_for_rollback, is_web_compatible_video
from spacemaker.ports.outbound.filesystem import FileSystemPort
from spacemaker.ports.outbound.media_converter import MediaConverterPort
from spacemaker.ports.outbound.media_probe import MediaProbePort


class ConvertMedia:
	def __init__(
		self,
		filesystem: FileSystemPort,
		converter: MediaConverterPort,
		probe: MediaProbePort,
	) -> None:
		self._filesystem = filesystem
		self._converter = converter
		self._probe = probe
		self.last_failure: str = ""

	def run(
		self,
		library_root: str,
		*,
		on_progress: Callable[[JobProgress], None] | None = None,
	) -> JobProgress:
		self.last_failure = ""
		rel_paths = self._filesystem.list_files_in_library_folder(library_root, LibraryFolder.ORIGINALS)
		total = len(rel_paths)
		completed = 0
		for rel in rel_paths:
			self._process_file(library_root, rel)
			completed += 1
			self._emit(on_progress, completed, total)
		return JobProgress(completed=completed, total=total)

	def _process_file(self, library_root: str, relative: str) -> None:
		source = self._filesystem.library_path(library_root, LibraryFolder.ORIGINALS, relative)
		video_probe = self._video_probe_for(relative, source)
		kind = media_kind_for_extension(normalize_extension(relative))
		if kind is MediaKind.VIDEO and video_probe is None and not relative.lower().endswith(".av1.mp4"):
			self._move_to_folder(library_root, relative, LibraryFolder.INVALID)
			return
		route = route_before_encode(relative, video_probe=video_probe)
		if route is ConversionRoute.INVALID:
			self._move_to_folder(library_root, relative, LibraryFolder.INVALID)
			return
		if route is ConversionRoute.MOVE_AS_IS:
			self._move_to_folder(library_root, relative, LibraryFolder.CONVERTED)
			return
		if self._try_skip_existing_valid(library_root, relative):
			return
		self._encode_with_retry(library_root, relative, video_probe)

	def _video_probe_for(self, relative: str, source: str) -> VideoProbe | None:
		if media_kind_for_extension(normalize_extension(relative)) is not MediaKind.VIDEO:
			return None
		return self._probe.probe_video(source)

	def _try_skip_existing_valid(self, library_root: str, relative: str) -> bool:
		out_rel = self._planned_output_relative(library_root, relative)
		dest = self._filesystem.library_path(library_root, LibraryFolder.CONVERTED, out_rel)
		if not self._filesystem.exists(dest) or self._filesystem.file_size(dest) <= 0:
			return False
		if not self._output_valid(relative, dest):
			return False
		self._filesystem.delete_file(
			self._filesystem.library_path(library_root, LibraryFolder.ORIGINALS, relative),
		)
		return True

	def _encode_with_retry(self, library_root: str, relative: str, video_probe: VideoProbe | None) -> None:
		for _ in range(2):
			ok = self._encode_once(library_root, relative, video_probe)
			if ok:
				return
		self._move_to_folder(library_root, relative, LibraryFolder.ERROR)

	def _encode_once(self, library_root: str, relative: str, video_probe: VideoProbe | None) -> bool:
		source = self._filesystem.library_path(library_root, LibraryFolder.ORIGINALS, relative)
		out_rel = self._planned_output_relative(library_root, relative)
		dest = self._filesystem.library_path(library_root, LibraryFolder.CONVERTED, out_rel)
		self._filesystem.ensure_parent_directory(dest)
		if self._filesystem.exists(dest):
			self._filesystem.delete_file(dest)
		ext = normalize_extension(relative)
		try:
			if media_kind_for_extension(ext) is MediaKind.IMAGE:
				if not self._probe.image_readable(source):
					self._move_to_folder(library_root, relative, LibraryFolder.INVALID)
					return True
				self._converter.encode_image_to_avif(source, dest)
			else:
				if video_probe is None:
					self.last_failure = f"{relative}: could not probe video"
					return False
				self._converter.encode_video_to_av1(source, dest)
		except (OSError, RuntimeError) as exc:
			self.last_failure = f"{relative}: {exc}"
			if self._filesystem.exists(dest):
				self._filesystem.delete_file(dest)
			return False
		if not self._output_valid(relative, dest):
			self.last_failure = f"{relative}: encoded output failed validation"
			if self._filesystem.exists(dest):
				self._filesystem.delete_file(dest)
			return False
		source_size = self._filesystem.file_size(source)
		output_size = self._filesystem.file_size(dest)
		if output_exceeds_rollback_threshold(source_size, output_size):
			if self._should_rollback_source(relative, video_probe):
				self._filesystem.delete_file(dest)
				self._move_to_folder(library_root, relative, LibraryFolder.CONVERTED)
				return True
		self._filesystem.delete_file(source)
		return True

	def _should_rollback_source(self, relative: str, video_probe: VideoProbe | None) -> bool:
		if video_probe is not None:
			return is_web_compatible_video(video_probe)
		return is_web_compatible_image_for_rollback(relative)

	def _output_valid(self, relative: str, dest: str) -> bool:
		if media_kind_for_extension(normalize_extension(relative)) is MediaKind.IMAGE:
			return self._probe.output_valid_image(dest)
		return self._probe.output_valid_video(dest)

	def _planned_output_relative(self, library_root: str, relative: str) -> str:
		ext = normalize_extension(relative)
		if media_kind_for_extension(ext) is MediaKind.IMAGE:
			stem_avif = image_avif_relative_path(relative, collision_avif_exists=False)
			collision = self._filesystem.exists(
				self._filesystem.library_path(library_root, LibraryFolder.CONVERTED, stem_avif),
			)
			return image_avif_relative_path(relative, collision_avif_exists=collision)
		return video_av1_relative_path(relative)

	def _move_to_folder(self, library_root: str, relative: str, folder: LibraryFolder) -> None:
		source = self._filesystem.library_path(library_root, LibraryFolder.ORIGINALS, relative)
		dest = self._filesystem.library_path(library_root, folder, relative)
		self._filesystem.move_file(source, dest)

	def _emit(
		self,
		on_progress: Callable[[JobProgress], None] | None,
		completed: int,
		total: int,
	) -> None:
		if on_progress is not None:
			on_progress(JobProgress(completed=completed, total=total))
