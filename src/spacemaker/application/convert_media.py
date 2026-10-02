from __future__ import annotations

import logging
from collections.abc import Callable

from spacemaker.domain.conversion import (
	ConversionRoute,
	image_avif_relative_path,
	output_exceeds_rollback_threshold,
	route_before_encode,
	unique_relative_path,
	video_av1_relative_path,
)
from spacemaker.domain.extract_control import ExtractJobControl
from spacemaker.domain.gallery_cache_paths import convert_staging_path, convert_staging_root
from spacemaker.domain.library import JobProgress, LibraryFolder
from spacemaker.domain.media import MediaKind, media_kind_for_extension, normalize_extension
from spacemaker.domain.video_encode import HardwareVideoEncoder, video_h264_web_relative_path
from spacemaker.domain.web_compat import VideoProbe, is_web_compatible_image_for_rollback, is_web_compatible_video
from spacemaker.ports.outbound.filesystem import FileSystemPort
from spacemaker.ports.outbound.media_converter import MediaConverterPort
from spacemaker.ports.outbound.media_probe import MediaProbePort


logger = logging.getLogger(__name__)


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
		control: ExtractJobControl | None = None,
		on_progress: Callable[[JobProgress], None] | None = None,
	) -> JobProgress:
		self.last_failure = ""
		self._filesystem.delete_directory(convert_staging_root(library_root))
		rel_paths = self._filesystem.list_files_in_library_folder(library_root, LibraryFolder.ORIGINALS)
		total = len(rel_paths)
		completed = 0
		self._emit(on_progress, completed, total)
		for rel in rel_paths:
			if control is not None and not control.before_next_file():
				break
			self._process_file(library_root, rel)
			completed += 1
			self._emit(on_progress, completed, total)
			if control is not None:
				control.after_file()
		return JobProgress(completed=completed, total=total)

	def _process_file(self, library_root: str, relative: str) -> None:
		source = self._filesystem.library_path(library_root, LibraryFolder.ORIGINALS, relative)
		try:
			video_probe = self._video_probe_for(relative, source)
		except FileNotFoundError as exc:
			self.last_failure = f"{relative}: {exc}"
			logger.warning(self.last_failure)
			self._move_to_folder(library_root, relative, LibraryFolder.ERROR)
			return
		kind = media_kind_for_extension(normalize_extension(relative))
		if kind is MediaKind.VIDEO and video_probe is None and not relative.lower().endswith(".av1.mp4"):
			self._move_to_folder(library_root, relative, LibraryFolder.INVALID)
			return
		route = route_before_encode(relative, video_probe=video_probe)
		if route is ConversionRoute.INVALID:
			self._move_to_folder(library_root, relative, LibraryFolder.INVALID)
			return
		if route is ConversionRoute.MOVE_AS_IS:
			self._move_to_folder(library_root, relative, LibraryFolder.PROCESSED)
			return
		if kind is MediaKind.VIDEO and self._converter.library_video_encoder() is HardwareVideoEncoder.NONE:
			if route is ConversionRoute.ENCODE:
				self.last_failure = f"{relative}: no hardware video encoder available; kept original in gallery"
				logger.warning(self.last_failure)
			self._move_to_folder(library_root, relative, LibraryFolder.PROCESSED)
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
		dest = self._filesystem.library_path(library_root, LibraryFolder.PROCESSED, out_rel)
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
		logger.error("%s: encode failed twice, moved to error/ (%s)", relative, self.last_failure)
		self._move_to_folder(library_root, relative, LibraryFolder.ERROR)

	def _encode_once(self, library_root: str, relative: str, video_probe: VideoProbe | None) -> bool:
		source = self._filesystem.library_path(library_root, LibraryFolder.ORIGINALS, relative)
		out_rel = self._planned_output_relative(library_root, relative)
		dest = self._filesystem.library_path(library_root, LibraryFolder.PROCESSED, out_rel)
		staging = convert_staging_path(library_root, out_rel)
		self._filesystem.ensure_parent_directory(staging)
		if self._filesystem.exists(staging):
			self._filesystem.delete_file(staging)
		ext = normalize_extension(relative)
		try:
			if media_kind_for_extension(ext) is MediaKind.IMAGE:
				if not self._probe.image_readable(source):
					self._move_to_folder(library_root, relative, LibraryFolder.INVALID)
					return True
				self._converter.encode_image_to_avif(source, staging)
			else:
				if video_probe is None:
					self.last_failure = f"{relative}: could not probe video"
					logger.warning(self.last_failure)
					return False
				encoder = self._converter.library_video_encoder()
				if encoder is HardwareVideoEncoder.AV1:
					self._converter.encode_video_to_av1(source, staging)
				elif encoder is HardwareVideoEncoder.H264:
					self._converter.encode_video_to_h264_aac(source, staging)
				else:
					self.last_failure = f"{relative}: no hardware video encoder"
					logger.warning(self.last_failure)
					return False
		except (OSError, RuntimeError) as exc:
			self.last_failure = f"{relative}: {exc}"
			logger.warning(self.last_failure)
			if self._filesystem.exists(staging):
				self._filesystem.delete_file(staging)
			return False
		if not self._output_valid(relative, staging):
			self.last_failure = f"{relative}: encoded output failed validation"
			logger.warning(self.last_failure)
			if self._filesystem.exists(staging):
				self._filesystem.delete_file(staging)
			return False
		if self._duplicates_plain_output(library_root, relative, out_rel, staging):
			# Same source encoded with the same settings is byte-identical: this file already exists
			# under its plain name (e.g. an interrupted earlier run), so keep one copy.
			self._filesystem.delete_file(staging)
			self._filesystem.delete_file(source)
			return True
		source_size = self._filesystem.file_size(source)
		output_size = self._filesystem.file_size(staging)
		if output_exceeds_rollback_threshold(source_size, output_size):
			if self._should_rollback_source(relative, video_probe):
				self._filesystem.delete_file(staging)
				self._move_to_folder(library_root, relative, LibraryFolder.PROCESSED)
				return True
		if self._filesystem.exists(dest):
			self._filesystem.delete_file(dest)
		self._filesystem.move_file(staging, dest)
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
			collision = self._processed_exists(library_root, stem_avif)
			return image_avif_relative_path(relative, collision_avif_exists=collision)
		encoder = self._converter.library_video_encoder()
		if encoder is HardwareVideoEncoder.H264:
			plain = video_h264_web_relative_path(relative)
			return video_h264_web_relative_path(relative, collision_exists=self._processed_exists(library_root, plain))
		plain = video_av1_relative_path(relative)
		return video_av1_relative_path(relative, collision_exists=self._processed_exists(library_root, plain))

	def _plain_output_relative(self, relative: str) -> str:
		if media_kind_for_extension(normalize_extension(relative)) is MediaKind.IMAGE:
			return image_avif_relative_path(relative, collision_avif_exists=False)
		if self._converter.library_video_encoder() is HardwareVideoEncoder.H264:
			return video_h264_web_relative_path(relative)
		return video_av1_relative_path(relative)

	def _duplicates_plain_output(self, library_root: str, relative: str, out_rel: str, staging: str) -> bool:
		plain = self._plain_output_relative(relative)
		if plain == out_rel:
			return False
		plain_path = self._filesystem.library_path(library_root, LibraryFolder.PROCESSED, plain)
		return self._filesystem.exists(plain_path) and self._filesystem.files_have_same_content(staging, plain_path)

	def _processed_exists(self, library_root: str, relative: str) -> bool:
		return self._filesystem.exists(self._filesystem.library_path(library_root, LibraryFolder.PROCESSED, relative))

	def _move_to_folder(self, library_root: str, relative: str, folder: LibraryFolder) -> None:
		source = self._filesystem.library_path(library_root, LibraryFolder.ORIGINALS, relative)
		dest_relative = relative
		dest = self._filesystem.library_path(library_root, folder, relative)
		if self._filesystem.exists(dest):
			if self._filesystem.files_have_same_content(source, dest):
				# Byte-identical file already there (e.g. a re-upload): keep one copy.
				self._filesystem.delete_file(source)
				return
			# A different file with the same name must never replace the one already filed.
			dest_relative = unique_relative_path(
				relative,
				lambda rel: self._filesystem.exists(self._filesystem.library_path(library_root, folder, rel)),
			)
			dest = self._filesystem.library_path(library_root, folder, dest_relative)
		self._filesystem.move_file(source, dest)

	def _emit(
		self,
		on_progress: Callable[[JobProgress], None] | None,
		completed: int,
		total: int,
	) -> None:
		if on_progress is not None:
			on_progress(JobProgress(completed=completed, total=total))
