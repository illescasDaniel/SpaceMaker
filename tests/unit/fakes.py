from __future__ import annotations

from dataclasses import dataclass, field

from spacemaker.domain.library import LibraryFolder
from spacemaker.domain.library_paths import skip_library_relative_path
from spacemaker.domain.web_compat import VideoProbe
from spacemaker.ports.outbound.device_repository import DeviceInfo


@dataclass
class FakeFileSystem:
	files: dict[str, int] = field(default_factory=dict)
	dirs: set[str] = field(default_factory=set)

	def ensure_library_folders(self, library_root: str) -> None:
		for folder in LibraryFolder:
			self.dirs.add(f"{library_root}/{folder.value}")

	def file_size(self, path: str) -> int:
		return self.files.get(path, 0)

	def exists(self, path: str) -> bool:
		return path in self.files

	def move_file(self, source: str, destination: str) -> None:
		if source not in self.files:
			raise FileNotFoundError(source)
		self.ensure_parent_directory(destination)
		self.files[destination] = self.files.pop(source)

	def ensure_parent_directory(self, file_path: str) -> None:
		parent = file_path.rpartition("/")[0]
		if parent:
			self.dirs.add(parent)

	def delete_file(self, path: str) -> None:
		self.files.pop(path, None)

	def list_files_recursive(self, folder: str) -> list[str]:
		prefix = folder.rstrip("/") + "/"
		out: list[str] = []
		for path in self.files:
			if path.startswith(prefix):
				out.append(path[len(prefix) :])
		return sorted(out)

	def list_files_in_library_folder(self, library_root: str, folder: LibraryFolder) -> list[str]:
		prefix = f"{library_root}/{folder.value}/"
		out: list[str] = []
		for path in self.files:
			if path.startswith(prefix):
				rel = path[len(prefix) :]
				if skip_library_relative_path(rel):
					continue
				out.append(rel)
		return sorted(out)

	def count_files_in_folder(self, library_root: str, folder: LibraryFolder) -> int:
		return len(self.list_files_in_library_folder(library_root, folder))

	def library_path(self, library_root: str, folder: LibraryFolder, relative: str) -> str:
		base = f"{library_root}/{folder.value}"
		if not relative:
			return base
		return f"{base}/{relative}"


@dataclass
class FakeDeviceRepository:
	devices: list[DeviceInfo] = field(default_factory=list)
	media_paths: list[str] = field(default_factory=list)
	sizes: dict[str, int] = field(default_factory=dict)
	pulled: list[tuple[str, str, str]] = field(default_factory=list)
	deleted: list[tuple[str, str]] = field(default_factory=list)

	def list_devices(self) -> list[DeviceInfo]:
		return list(self.devices)

	def list_media_paths(self, device_id: str) -> list[str]:
		_ = device_id
		return list(self.media_paths)

	def remote_file_size(self, device_id: str, device_path: str) -> int:
		_ = device_id
		return self.sizes.get(device_path, 0)

	def pull_file(self, device_id: str, device_path: str, local_path: str) -> None:
		size = self.sizes.get(device_path, 100)
		self.pulled.append((device_id, device_path, local_path))
		self.files_set(local_path, size)

	def delete_device_file(self, device_id: str, device_path: str) -> None:
		self.deleted.append((device_id, device_path))

	def files_set(self, path: str, size: int) -> None:
		# helper for tests to sync with filesystem fake
		self._fs.files[path] = size

	_fs: FakeFileSystem = field(default_factory=FakeFileSystem)

	def bind_filesystem(self, fs: FakeFileSystem) -> None:
		self._fs = fs


@dataclass
class FakeMediaProbe:
	videos: dict[str, VideoProbe | None] = field(default_factory=dict)
	readable_images: set[str] = field(default_factory=set)
	valid_images: set[str] = field(default_factory=set)
	valid_videos: set[str] = field(default_factory=set)

	def probe_video(self, path: str) -> VideoProbe | None:
		return self.videos.get(path)

	def image_readable(self, path: str) -> bool:
		return path in self.readable_images

	def output_valid_image(self, path: str) -> bool:
		return path in self.valid_images

	def output_valid_video(self, path: str) -> bool:
		return path in self.valid_videos


@dataclass
class FakeMediaConverter:
	encoded_images: list[tuple[str, str]] = field(default_factory=list)
	encoded_videos: list[tuple[str, str]] = field(default_factory=list)
	fail_destinations: set[str] = field(default_factory=set)
	output_sizes: dict[str, int] = field(default_factory=dict)

	def encode_image_to_avif(self, source: str, destination: str) -> None:
		if destination in self.fail_destinations:
			raise RuntimeError("encode failed")
		self.encoded_images.append((source, destination))
		self._fs.files[destination] = self.output_sizes.get(destination, 50)

	def encode_video_to_av1(self, source: str, destination: str) -> None:
		if destination in self.fail_destinations:
			raise RuntimeError("encode failed")
		self.encoded_videos.append((source, destination))
		self._fs.files[destination] = self.output_sizes.get(destination, 50)

	_fs: FakeFileSystem = field(default_factory=FakeFileSystem)

	def bind_filesystem(self, fs: FakeFileSystem) -> None:
		self._fs = fs
