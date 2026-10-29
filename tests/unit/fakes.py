from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.device_browse import DeviceBrowseError, DeviceBrowseErrorKind, DeviceBrowseSort, DeviceEntry
from spacemaker.domain.device_preview import (
	CachedDevicePreview,
	DevicePreviewError,
	DevicePreviewErrorKind,
	VideoPoster,
)
from spacemaker.domain.device_view import (
	EMPTY_VIEW_MEMORY,
	DeviceViewMemory,
	DeviceViewSetting,
	remember_view,
)
from spacemaker.domain.gallery import GalleryItem
from spacemaker.domain.gallery_batch import ArchiveEntry, TrashError, VideoExportEncoder
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
	identical_pairs: set[frozenset[str]] = field(default_factory=set)
	temp_files_created: list[str] = field(default_factory=list)

	def make_temp_file(self, suffix: str) -> str:
		self.temp_files_created.append(f"fake-temp/preview-{len(self.temp_files_created)}{suffix}")
		path = self.temp_files_created[-1]
		self.files[path] = 0
		return path

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

	def files_have_same_content(self, first: str, second: str) -> bool:
		return frozenset({first, second}) in self.identical_pairs

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

	def delete_directory(self, path: str) -> None:
		prefix = path.rstrip("/") + "/"
		for key in list(self.files):
			if key == path or key.startswith(prefix):
				self.files.pop(key, None)
		self.dirs.discard(path)
		for d in list(self.dirs):
			if d.startswith(prefix):
				self.dirs.discard(d)
		target = Path(path)
		if target.is_dir():
			import shutil

			shutil.rmtree(target, ignore_errors=True)
		elif target.is_file():
			target.unlink(missing_ok=True)

	def list_files_recursive(self, folder: str) -> list[str]:
		prefix = folder.replace("\\", "/").rstrip("/") + "/"
		out: list[str] = []
		for path in self.files:
			normalized = path.replace("\\", "/")
			if normalized.startswith(prefix):
				out.append(normalized[len(prefix) :])
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
	file_paths: list[str] | None = None
	sizes: dict[str, int] = field(default_factory=dict)
	pulled: list[tuple[str, str, str]] = field(default_factory=list)
	deleted: list[tuple[str, str]] = field(default_factory=list)
	tree: dict[str, list[DeviceEntry]] = field(default_factory=dict)
	browse_errors: dict[str, DeviceBrowseErrorKind] = field(default_factory=dict)
	list_directory_calls: list[str] = field(default_factory=list)
	# device previews: per-path scripted data and recorded calls
	stat_entries: dict[str, DeviceEntry] = field(default_factory=dict)
	heads: dict[str, bytes] = field(default_factory=dict)
	stat_errors: dict[str, DeviceBrowseErrorKind] = field(default_factory=dict)
	head_errors: dict[str, DeviceBrowseErrorKind] = field(default_factory=dict)
	pull_errors: dict[str, DeviceBrowseErrorKind] = field(default_factory=dict)
	stat_calls: list[str] = field(default_factory=list)
	read_head_calls: list[tuple[str, str, int, float]] = field(default_factory=list)
	pull_timeout_calls: list[tuple[str, str, float]] = field(default_factory=list)
	head_gates: dict[str, threading.Event] = field(default_factory=dict)
	"""Per device id: ``read_head`` blocks until the event is set (to test the concurrency cap)."""
	active_heads: dict[str, int] = field(default_factory=dict)
	peak_heads: dict[str, int] = field(default_factory=dict)
	head_entered: threading.Semaphore = field(default_factory=lambda: threading.Semaphore(0))
	"""Released once per ``read_head`` entry; tests acquire it to wait for N reads to have started."""
	_head_lock: threading.Lock = field(default_factory=threading.Lock)
	# video streaming: per-path file bytes served by ``read_range`` and recorded calls
	range_data: dict[str, bytes] = field(default_factory=dict)
	range_errors: dict[str, DeviceBrowseErrorKind] = field(default_factory=dict)
	read_range_calls: list[tuple[str, str, int, int, float]] = field(default_factory=list)

	@property
	def device_calls(self) -> int:
		return (
			len(self.stat_calls) + len(self.read_head_calls) + len(self.pull_timeout_calls) + len(self.read_range_calls)
		)

	def list_devices(self) -> list[DeviceInfo]:
		return list(self.devices)

	def list_media_paths(self, device_id: str) -> list[str]:
		_ = device_id
		return list(self.media_paths)

	def list_file_paths(self, device_id: str) -> list[str]:
		_ = device_id
		if self.file_paths is not None:
			return list(self.file_paths)
		return list(self.media_paths)

	def list_extra_file_paths(self, device_id: str, extras: frozenset[str]) -> list[str]:
		from spacemaker.domain.transfer_folders import path_matches_extra_sources

		return [p for p in self.list_file_paths(device_id) if path_matches_extra_sources(p, extras)]

	def list_directory(self, device_id: str, path: str) -> list[DeviceEntry]:
		_ = device_id
		self.list_directory_calls.append(path)
		if path in self.browse_errors:
			raise DeviceBrowseError(self.browse_errors[path])
		return list(self.tree.get(path, []))

	def stat_file(self, device_id: str, path: str) -> DeviceEntry:
		_ = device_id
		self.stat_calls.append(path)
		if path in self.stat_errors:
			raise DeviceBrowseError(self.stat_errors[path])
		if path not in self.stat_entries:
			raise DeviceBrowseError(DeviceBrowseErrorKind.NOT_FOUND)
		return self.stat_entries[path]

	def read_head(self, device_id: str, path: str, max_bytes: int, timeout_s: float) -> bytes:
		self.read_head_calls.append((device_id, path, max_bytes, timeout_s))
		with self._head_lock:
			active = self.active_heads.get(device_id, 0) + 1
			self.active_heads[device_id] = active
			self.peak_heads[device_id] = max(self.peak_heads.get(device_id, 0), active)
		self.head_entered.release()
		try:
			gate = self.head_gates.get(device_id)
			if gate is not None:
				gate.wait(timeout=5)
			if path in self.head_errors:
				raise DeviceBrowseError(self.head_errors[path])
			return self.heads.get(path, b"")[:max_bytes]
		finally:
			with self._head_lock:
				self.active_heads[device_id] -= 1

	def read_range(self, device_id: str, path: str, offset: int, length: int, timeout_s: float) -> bytes:
		self.read_range_calls.append((device_id, path, offset, length, timeout_s))
		if path in self.range_errors:
			raise DeviceBrowseError(self.range_errors[path])
		return self.range_data.get(path, b"")[offset : offset + length]

	def pull_file_with_timeout(self, device_id: str, path: str, local_path: str, timeout_s: float) -> None:
		_ = device_id
		self.pull_timeout_calls.append((path, local_path, timeout_s))
		self.files_set(local_path, 1)  # a (partial) file exists even when the pull then fails
		if path in self.pull_errors:
			raise DeviceBrowseError(self.pull_errors[path])

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
		self.captured_at_calls.append(path)
		p = Path(path)
		size = self._fs.files.get(path, 0) if hasattr(self, "_fs") else 0
		return GalleryDisplayMetadata(
			filename=p.name,
			captured_at=self.captured_at_map.get(path),
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
	friendly_encoder: VideoExportEncoder = VideoExportEncoder.HARDWARE_H264
	h264_use_cpu_flags: list[bool] = field(default_factory=list)

	def library_video_encoder(self) -> HardwareVideoEncoder:
		return self.library_encoder

	def friendly_video_encoder(self) -> VideoExportEncoder:
		return self.friendly_encoder

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
		if destination in self.fail_destinations or source in self.fail_destinations:
			raise RuntimeError("encode failed")
		self.encoded_jpegs.append((source, destination))
		size = self.output_sizes.get(destination, 50)
		self._fs.files[destination] = size
		dest = Path(destination)
		dest.parent.mkdir(parents=True, exist_ok=True)
		dest.write_bytes(b"x" * size)

	@staticmethod
	def _write_real(destination: str, size: int) -> None:
		"""Export tests use real tmp dirs; library-convert tests use fake paths that cannot be created."""
		try:
			dest = Path(destination)
			dest.parent.mkdir(parents=True, exist_ok=True)
			dest.write_bytes(b"x" * size)
		except OSError:
			pass

	def encode_video_to_h264_aac(
		self, source: str, destination: str, *, on_progress=None, use_cpu: bool = False
	) -> None:
		if destination in self.fail_destinations or source in self.fail_destinations:
			raise RuntimeError("encode failed")
		if on_progress:
			on_progress(50)
		self.encoded_h264.append((source, destination))
		self.h264_use_cpu_flags.append(use_cpu)
		size = self.output_sizes.get(destination, 50)
		self._fs.files[destination] = size
		self._write_real(destination, size)
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

	async def snapshot_stats(self, library_root: str) -> dict[str, FileStat]:
		return {rel: FileStat(mtime=row.mtime, size=row.size) for rel, row in self._bucket(library_root).items()}

	async def apply_sync(self, library_root: str, *, upserts: list[GalleryIndexRow], removed: list[str]) -> None:
		bucket = self._bucket(library_root)
		for row in upserts:
			bucket[row.relative_path] = row
		for relative_path in removed:
			bucket.pop(relative_path, None)

	async def remove(self, library_root: str, relative_path: str) -> None:
		self._bucket(library_root).pop(relative_path, None)

	async def get(self, library_root: str, relative_path: str) -> GalleryIndexRow | None:
		return self._bucket(library_root).get(relative_path)

	async def page(self, library_root: str, *, cursor: GalleryCursor | None, limit: int) -> GalleryPage:
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

	async def days_with_media(self, library_root: str, year: int, month: int) -> list[int]:
		return sorted(
			{
				r.captured_at.day
				for r in self._bucket(library_root).values()
				if r.captured_at.year == year and r.captured_at.month == month
			}
		)

	async def items_for_day(self, library_root: str, year: int, month: int, day: int) -> list[GalleryItem]:
		return [
			r.as_item()
			for r in self._sorted_rows(library_root)
			if r.captured_at.year == year and r.captured_at.month == month and r.captured_at.day == day
		]

	async def neighbor(
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

	async def count(self, library_root: str) -> int:
		return len(self._bucket(library_root))

	async def close(self, library_root: str) -> None:
		self.rows.pop(library_root, None)


@dataclass
class FakeTrash:
	"""Records trashed paths; ``fail_paths`` raise TrashError and leave the file untouched."""

	trashed: list[str] = field(default_factory=list)
	fail_paths: set[str] = field(default_factory=set)
	delete_calls: list[str] = field(default_factory=list)

	def move_to_trash(self, path: str) -> None:
		if path in self.fail_paths:
			raise TrashError("trash unavailable")
		self.trashed.append(path)
		Path(path).unlink()


@dataclass
class FakeDiskSpace:
	free: int = 10**12

	def free_bytes(self, path: str) -> int:
		_ = path
		return self.free


@dataclass
class FakeArchiveWriter:
	written: list[tuple[str, list[ArchiveEntry]]] = field(default_factory=list)
	error: OSError | None = None

	def write_stored_zip(self, destination: str, entries, *, skip_missing: bool = False) -> int:
		if self.error is not None:
			raise self.error
		kept = [entry for entry in entries if not skip_missing or Path(entry.source_path).exists()]
		self.written.append((destination, kept))
		Path(destination).parent.mkdir(parents=True, exist_ok=True)
		Path(destination).write_bytes(b"zip")
		return len(kept)


@dataclass
class FakeUserPreferences:
	"""In-memory ``UserPreferencesPort``; ``picker_sort_writes`` records every ``set_device_picker_sort``."""

	compress_media: bool | None = None
	usb_transfer_destination: str | None = None
	device_picker_sort: DeviceBrowseSort | None = None
	picker_sort_writes: list[DeviceBrowseSort | None] = field(default_factory=list)
	device_picker_views: DeviceViewMemory = EMPTY_VIEW_MEMORY
	picker_view_writes: list[tuple[str, DeviceViewSetting]] = field(default_factory=list)

	def get_compress_media(self) -> bool | None:
		return self.compress_media

	def set_compress_media(self, enabled: bool) -> None:
		self.compress_media = enabled

	def get_usb_transfer_destination(self) -> str | None:
		return self.usb_transfer_destination

	def set_usb_transfer_destination(self, path: str | None) -> None:
		self.usb_transfer_destination = path or None

	def get_device_picker_sort(self) -> DeviceBrowseSort | None:
		return self.device_picker_sort

	def set_device_picker_sort(self, sort: DeviceBrowseSort | None) -> None:
		self.picker_sort_writes.append(sort)
		self.device_picker_sort = sort

	def get_device_picker_views(self) -> DeviceViewMemory:
		return self.device_picker_views

	def set_device_picker_view(self, path: str, setting: DeviceViewSetting) -> None:
		self.picker_view_writes.append((path, setting))
		self.device_picker_views = remember_view(self.device_picker_views, path, setting)

	def clear(self) -> None:
		self.compress_media = None
		self.usb_transfer_destination = None
		self.device_picker_sort = None
		self.device_picker_views = EMPTY_VIEW_MEMORY


@dataclass
class FakePreviewImaging:
	"""``PreviewImagingPort`` fake: ``embedded`` is what ``thumbnail_from_head`` finds, ``rendered`` what ``render_jpeg`` returns."""

	embedded: bytes | None = None
	rendered: bytes = b"rendered-jpeg"
	render_error: DevicePreviewErrorKind | None = None
	filesystem: FakeFileSystem | None = None
	head_calls: list[tuple[bytes, int]] = field(default_factory=list)
	render_calls: list[tuple[str, int, float]] = field(default_factory=list)
	embedded_rendered: bytes = b"rendered-embedded-jpeg"
	render_embedded_calls: list[tuple[bytes, int, int, float]] = field(default_factory=list)
	source_existed_at_render: list[bool] = field(default_factory=list)

	def thumbnail_from_head(self, head: bytes, max_edge: int) -> bytes | None:
		self.head_calls.append((head, max_edge))
		return self.embedded

	def render_jpeg(self, source_path: str, max_edge: int, timeout_s: float) -> bytes:
		self.render_calls.append((source_path, max_edge, timeout_s))
		if self.filesystem is not None:
			self.source_existed_at_render.append(source_path in self.filesystem.files)
		if self.render_error is not None:
			raise DevicePreviewError(self.render_error)
		return self.rendered

	def render_embedded_jpeg(self, jpeg: bytes, max_edge: int, fallback_orientation: int, timeout_s: float) -> bytes:
		self.render_embedded_calls.append((jpeg, max_edge, fallback_orientation, timeout_s))
		if self.render_error is not None:
			raise DevicePreviewError(self.render_error)
		return self.embedded_rendered


@dataclass
class FakeVideoPoster:
	"""``VideoPosterPort`` fake: returns ``poster`` or raises ``error``; records every call.

	``on_render`` runs inside ``render_poster`` with the source URL (tests use it to inspect the live token);
	``gate`` blocks the render until set (concurrency-cap tests) and ``entered`` is released once per entry.
	"""

	poster: VideoPoster = field(default_factory=lambda: VideoPoster(b"poster-jpeg", 42.37))
	error: DevicePreviewErrorKind | None = None
	calls: list[tuple[str, int, float]] = field(default_factory=list)
	cancels: list[threading.Event | None] = field(default_factory=list)
	on_render: Callable[[str], None] | None = None
	gate: threading.Event | None = None
	entered: threading.Semaphore = field(default_factory=lambda: threading.Semaphore(0))
	active: int = 0
	peak: int = 0
	_lock: threading.Lock = field(default_factory=threading.Lock)

	def render_poster(
		self, source_url: str, max_edge: int, timeout_s: float, cancel: threading.Event | None = None
	) -> VideoPoster:
		self.cancels.append(cancel)
		self.calls.append((source_url, max_edge, timeout_s))
		with self._lock:
			self.active += 1
			self.peak = max(self.peak, self.active)
		self.entered.release()
		try:
			if self.on_render is not None:
				self.on_render(source_url)
			if cancel is not None and cancel.is_set():  # like the real adapter: killed ffmpeg -> timeout
				raise DevicePreviewError(DevicePreviewErrorKind.TIMEOUT)
			if self.gate is not None:
				self.gate.wait(timeout=5)
			if self.error is not None:
				raise DevicePreviewError(self.error)
			return self.poster
		finally:
			with self._lock:
				self.active -= 1


@dataclass
class FakeDevicePreviewCache:
	store: dict[str, CachedDevicePreview] = field(default_factory=dict)
	get_calls: list[str] = field(default_factory=list)
	put_calls: list[tuple[str, CachedDevicePreview]] = field(default_factory=list)

	def get(self, key: str) -> CachedDevicePreview | None:
		self.get_calls.append(key)
		return self.store.get(key)

	def put(self, key: str, entry: CachedDevicePreview) -> None:
		self.put_calls.append((key, entry))
		self.store[key] = entry


@dataclass
class FakeDeviceActivity:
	busy: bool = False
	calls: list[tuple[ConnectionMethod, str]] = field(default_factory=list)

	def is_busy(self, method: ConnectionMethod, device_id: str) -> bool:
		self.calls.append((method, device_id))
		return self.busy
