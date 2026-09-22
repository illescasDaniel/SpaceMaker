from __future__ import annotations

from collections.abc import Callable

from spacemaker.domain.extract_control import ExtractJobControl
from spacemaker.domain.library import JobProgress, LibraryFolder, TransferMode
from spacemaker.domain.library_paths import skip_media_path
from spacemaker.domain.source_folders import ALL_SOURCE_FOLDERS, SourceFolder, path_matches_source_folders
from spacemaker.ports.outbound.device_repository import DeviceRepositoryPort
from spacemaker.ports.outbound.filesystem import FileSystemPort


class ExtractMedia:
	def __init__(
		self,
		devices: DeviceRepositoryPort,
		filesystem: FileSystemPort,
	) -> None:
		self._devices = devices
		self._filesystem = filesystem

	def run(
		self,
		library_root: str,
		device_id: str,
		mode: TransferMode,
		*,
		source_folders: frozenset[SourceFolder] | None = None,
		control: ExtractJobControl | None = None,
		on_progress: Callable[[JobProgress], None] | None = None,
	) -> JobProgress:
		self._filesystem.ensure_library_folders(library_root)
		selected = source_folders or ALL_SOURCE_FOLDERS
		paths = sorted(
			p
			for p in self._devices.list_media_paths(device_id)
			if path_matches_source_folders(p, selected) and not skip_media_path(p)
		)
		total = len(paths)
		completed = 0
		for device_path in paths:
			if control is not None and not control.before_next_file():
				break
			relative = device_path.lstrip("/")
			dest = self._filesystem.library_path(library_root, LibraryFolder.ORIGINALS, relative)
			if self._should_skip(device_path, device_id, dest):
				completed += 1
				self._emit(on_progress, completed, total)
				if control is not None:
					control.after_file()
				continue
			self._devices.pull_file(device_id, device_path, dest)
			if mode is TransferMode.MOVE:
				self._devices.delete_device_file(device_id, device_path)
			completed += 1
			self._emit(on_progress, completed, total)
			if control is not None:
				control.after_file()
		return JobProgress(completed=completed, total=total)

	def _should_skip(self, device_path: str, device_id: str, dest: str) -> bool:
		if not self._filesystem.exists(dest):
			return False
		remote = self._devices.remote_file_size(device_id, device_path)
		local = self._filesystem.file_size(dest)
		return remote > 0 and remote == local

	def _emit(
		self,
		on_progress: Callable[[JobProgress], None] | None,
		completed: int,
		total: int,
	) -> None:
		if on_progress is not None:
			on_progress(JobProgress(completed=completed, total=total))
