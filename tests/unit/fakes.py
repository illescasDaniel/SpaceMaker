from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from spacemaker.domain.gallery import GalleryItem
from spacemaker.domain.gallery_index import FileStat, GalleryCursor, GalleryIndexRow, GalleryPage
from spacemaker.domain.gallery_metadata import GalleryDisplayMetadata
from spacemaker.domain.library import LibraryFolder
from spacemaker.domain.library_paths import skip_library_relative_path
from spacemaker.domain.video_encode import HardwareVideoEncoder
from spacemaker.domain.web_compat import VideoProbe
from spacemaker.ports.outbound.device_repository import DeviceInfo


@dataclass
class FakeFileSystem:
	files: dict[str, int] = field(default_factory=dict)
	mtimes: dict[str, float] = field(default_factory=dict)
	dirs: set[str] = field(default_factory=set)

	def ensure_library_folders(self, library_root: str) -> None:
		for folder in LibraryFolder:
			self.dirs.add(f"{library_root}/{folder.value}")

	def file_size(self, path: str) -> int:
		return self.files.get(path, 0)

	def file_stat(self, path: str) -> FileStat:
		return FileStat(mtime=self.mtimes.get(path, 0.0), size=self.files.get(path, 0))

	def exists(self, path: str) -> bool:
		return path in self.files

	def move_file(self, source: str, destination: str) -> None:
		if source not in self.files:
			raise FileNotFoundError(source)
		self.ensure_parent_directory(destination)
		self.files[destination] = self.files.pop(source)

	def copy_file(self, source: str, destination: str) -> None:
		self.ensure_parent_directory(destination)
		if source in self.files:
			self.files[destination] = self.files[source]
			return
		src = Path(source)
		if src.is_file():
			self.files[destination] = src.stat().st_size
			return
		raise FileNotFoundError(source)

	def ensure_parent_directory(self, file_path: str) -> None:
		parent = file_path.rpartition("/")[0]
		if parent:
			self.dirs.add(parent)

	def delete_file(self, path: str) -> None:
		self.files.pop(path, None)
		Path(path).unlink(missing_ok=True)

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
	captured_at_map: dict[str, datetime] = field(default_factory=dict)
	captured_at_calls: list[str] = field(default_factory=list)

	def probe_video(self, path: str) -> VideoProbe | None:
		return self.videos.get(path)

	def image_readable(self, path: str) -> bool:
		return path in self.readable_images

	def output_valid_image(self, path: str) -> bool:
		return path in self.valid_images

	def output_valid_video(self, path: str) -> bool:
		return path in self.valid_videos

	def captured_at(self, path: str) -> datetime | None:
		self.captured_at_calls.append(path)
		return self.captured_at_map.get(path)

	def display_metadata(self, path: str) -> GalleryDisplayMetadata:
		p = Path(path)
		size = self._fs.files.get(path, 0) if hasattr(self, "_fs") else 0
		return GalleryDisplayMetadata(
			filename=p.name,
			captured_at=None,
			camera_make="",
			camera_model="",
			width=None,
			height=None,
			duration_seconds=None,
			file_size_bytes=size,
			gps="",
		)

	_fs: FakeFileSystem = field(default_factory=FakeFileSystem)

	def bind_filesystem(self, fs: FakeFileSystem) -> None:
		self._fs = fs


@dataclass
class FakeMediaConverter:
	library_encoder: HardwareVideoEncoder = HardwareVideoEncoder.AV1
	encoded_images: list[tuple[str, str]] = field(default_factory=list)
	encoded_jpegs: list[tuple[str, str]] = field(default_factory=list)
	encoded_videos: list[tuple[str, str]] = field(default_factory=list)
	encoded_h264: list[tuple[str, str]] = field(default_factory=list)
	fail_destinations: set[str] = field(default_factory=set)
	output_sizes: dict[str, int] = field(default_factory=dict)

	def library_video_encoder(self) -> HardwareVideoEncoder:
		return self.library_encoder

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

	def encode_image_to_jpeg(self, source: str, destination: str) -> None:
		if destination in self.fail_destinations:
			raise RuntimeError("encode failed")
		self.encoded_jpegs.append((source, destination))
		size = self.output_sizes.get(destination, 50)
		self._fs.files[destination] = size
		dest = Path(destination)
		dest.parent.mkdir(parents=True, exist_ok=True)
		dest.write_bytes(b"x" * size)

	def encode_video_to_h264_aac(self, source: str, destination: str, *, on_progress=None) -> None:
		if destination in self.fail_destinations:
			raise RuntimeError("encode failed")
		if on_progress:
			on_progress(50)
		self.encoded_h264.append((source, destination))
		self._fs.files[destination] = self.output_sizes.get(destination, 50)
		if on_progress:
			on_progress(100)

	_fs: FakeFileSystem = field(default_factory=FakeFileSystem)

	def bind_filesystem(self, fs: FakeFileSystem) -> None:
		self._fs = fs


@dataclass
class FakeGalleryIndex:
	rows: dict[str, dict[str, GalleryIndexRow]] = field(default_factory=dict)

	def _bucket(self, library_root: str) -> dict[str, GalleryIndexRow]:
		return self.rows.setdefault(library_root, {})

	def _sorted_rows(self, library_root: str) -> list[GalleryIndexRow]:
		return sorted(self._bucket(library_root).values(), key=lambda r: (r.captured_at, r.relative_path), reverse=True)

	def snapshot_stats(self, library_root: str) -> dict[str, FileStat]:
		return {rel: FileStat(mtime=row.mtime, size=row.size) for rel, row in self._bucket(library_root).items()}

	def apply_sync(self, library_root: str, *, upserts: list[GalleryIndexRow], removed: list[str]) -> None:
		bucket = self._bucket(library_root)
		for row in upserts:
			bucket[row.relative_path] = row
		for relative_path in removed:
			bucket.pop(relative_path, None)

	def remove(self, library_root: str, relative_path: str) -> None:
		self._bucket(library_root).pop(relative_path, None)

	def get(self, library_root: str, relative_path: str) -> GalleryIndexRow | None:
		return self._bucket(library_root).get(relative_path)

	def page(self, library_root: str, *, cursor: GalleryCursor | None, limit: int) -> GalleryPage:
		rows = self._sorted_rows(library_root)
		if cursor is not None:
			key = (cursor.captured_at, cursor.relative_path)
			rows = [r for r in rows if (r.captured_at, r.relative_path) < key]
		page_rows = rows[:limit]
		next_cursor = None
		if len(rows) > limit:
			last = page_rows[-1]
			next_cursor = GalleryCursor(captured_at=last.captured_at, relative_path=last.relative_path).encode()
		return GalleryPage(items=tuple(r.as_item() for r in page_rows), next_cursor=next_cursor)

	def days_with_media(self, library_root: str, year: int, month: int) -> list[int]:
		return sorted(
			{
				r.captured_at.day
				for r in self._bucket(library_root).values()
				if r.captured_at.year == year and r.captured_at.month == month
			}
		)

	def items_for_day(self, library_root: str, year: int, month: int, day: int) -> list[GalleryItem]:
		return [
			r.as_item()
			for r in self._sorted_rows(library_root)
			if r.captured_at.year == year and r.captured_at.month == month and r.captured_at.day == day
		]

	def neighbor(
		self, library_root: str, relative_path: str, *, direction: Literal["prev", "next"]
	) -> GalleryItem | None:
		rows = self._sorted_rows(library_root)
		index = next((i for i, r in enumerate(rows) if r.relative_path == relative_path), None)
		if index is None:
			return None
		target = index + 1 if direction == "next" else index - 1
		if target < 0 or target >= len(rows):
			return None
		return rows[target].as_item()

	def count(self, library_root: str) -> int:
		return len(self._bucket(library_root))
