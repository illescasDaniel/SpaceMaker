import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace

import pytest
from tests.unit.dng_builder import JPEG, DngFile, build_dng, jpeg_ifd
from tests.unit.fakes import (
	FakeDeviceActivity,
	FakeDevicePreviewCache,
	FakeDeviceRepository,
	FakeFileSystem,
	FakePreviewImaging,
	FakeVideoPoster,
)

from spacemaker.application.device_stream_tokens import DeviceStreamTokens
from spacemaker.application.get_device_preview import GetDevicePreview
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.device_browse import DeviceBrowseErrorKind, DeviceEntry
from spacemaker.domain.device_preview import (
	PREVIEW_FULL_PULL_MAX_BYTES,
	PREVIEW_FULL_TIMEOUT_S,
	PREVIEW_HEAD_BYTES,
	PREVIEW_HEAD_TIMEOUT_S,
	PREVIEW_MAX_CONCURRENT_READS,
	CachedDevicePreview,
	DevicePreviewError,
	DevicePreviewErrorKind,
	DevicePreviewKind,
	DevicePreviewRequest,
	device_preview_cache_key,
)
from spacemaker.domain.dng_preview import DNG_HEADER_READ_BYTES, DNG_HEADER_TIMEOUT_S, DNG_PREVIEW_TIMEOUT_S


PATH = "DCIM/Camera/IMG_0001.jpg"
MEGABYTE = 1024 * 1024


@dataclass
class _Rig:
	"""A ``GetDevicePreview`` wired with fakes, keeping the fakes reachable for assertions."""

	devices: FakeDeviceRepository = field(default_factory=FakeDeviceRepository)
	cache: FakeDevicePreviewCache = field(default_factory=FakeDevicePreviewCache)
	activity: FakeDeviceActivity = field(default_factory=FakeDeviceActivity)
	filesystem: FakeFileSystem = field(default_factory=FakeFileSystem)
	resolved: list[ConnectionMethod] = field(default_factory=list)

	def __post_init__(self) -> None:
		self.devices.bind_filesystem(self.filesystem)
		self.imaging = FakePreviewImaging(filesystem=self.filesystem)
		self.use_case = GetDevicePreview(
			self._resolve,
			self.cache,
			self.imaging,
			self.activity,
			self.filesystem,
			poster=FakeVideoPoster(),
			tokens=DeviceStreamTokens(),
			stream_url=lambda token: f"http://127.0.0.1/{token}",
		)

	def _resolve(self, method: ConnectionMethod) -> FakeDeviceRepository:
		self.resolved.append(method)
		return self.devices


def _request(
	path: str = PATH,
	kind: DevicePreviewKind = DevicePreviewKind.THUMB,
	size: int = 800_000,
	device_id: str = "dev1",
) -> DevicePreviewRequest:
	return DevicePreviewRequest(ConnectionMethod.ADB, device_id, path, size, 1_700_000_000, kind)


def _error_kind(rig: _Rig, request: DevicePreviewRequest) -> DevicePreviewErrorKind:
	with pytest.raises(DevicePreviewError) as raised:
		rig.use_case(request)
	return raised.value.kind


def test_given_embedded_thumbnail_when_thumb_then_one_head_read_and_no_pull_and_cached() -> None:
	# given
	rig = _Rig()
	rig.devices.heads[PATH] = b"exif-head"
	rig.imaging.embedded = b"embedded-jpeg"
	request = _request()
	# when
	preview = rig.use_case(request)
	# then
	assert preview.jpeg == b"embedded-jpeg"
	assert rig.devices.read_head_calls == [("dev1", PATH, PREVIEW_HEAD_BYTES, PREVIEW_HEAD_TIMEOUT_S)]
	assert rig.imaging.head_calls == [(b"exif-head", 320)]
	assert rig.devices.stat_calls == []
	assert rig.devices.pull_timeout_calls == []
	key = device_preview_cache_key(request)
	assert rig.cache.put_calls == [(key, CachedDevicePreview(b"embedded-jpeg"))]
	assert preview.etag.startswith('"')
	assert preview.etag.endswith('"')
	assert key in preview.etag


def test_given_no_embedded_thumbnail_when_thumb_then_pulls_renders_320_and_deletes_temp() -> None:
	# given
	rig = _Rig()
	rig.devices.stat_entries[PATH] = DeviceEntry("IMG_0001.jpg", False, size=800_000, mtime=1)
	rig.imaging.rendered = b"rendered-320"
	# when
	preview = rig.use_case(_request())
	# then
	assert preview.jpeg == b"rendered-320"
	assert rig.devices.stat_calls == [PATH]
	temp = rig.filesystem.temp_files_created[0]
	assert rig.devices.pull_timeout_calls == [(PATH, temp, PREVIEW_FULL_TIMEOUT_S)]
	assert rig.imaging.render_calls == [(temp, 320, PREVIEW_FULL_TIMEOUT_S)]
	assert rig.imaging.source_existed_at_render == [True]
	assert temp not in rig.filesystem.files
	assert rig.cache.put_calls == [(device_preview_cache_key(_request()), CachedDevicePreview(b"rendered-320"))]


def test_given_file_exactly_at_cap_when_fallback_then_still_pulled() -> None:
	# given
	rig = _Rig()
	rig.devices.stat_entries[PATH] = DeviceEntry("IMG_0001.jpg", False, size=PREVIEW_FULL_PULL_MAX_BYTES)
	# when
	preview = rig.use_case(_request())
	# then
	assert preview.jpeg == rig.imaging.rendered
	assert len(rig.devices.pull_timeout_calls) == 1


def test_given_real_size_over_cap_when_client_size_lies_small_then_too_large_without_pull() -> None:
	# given
	rig = _Rig()
	rig.devices.stat_entries[PATH] = DeviceEntry("PANO_0042.jpg", False, size=40 * MEGABYTE)
	request = _request(size=1_000)
	# when
	kind = _error_kind(rig, request)
	# then
	assert kind is DevicePreviewErrorKind.TOO_LARGE
	assert rig.devices.pull_timeout_calls == []
	assert rig.filesystem.temp_files_created == []
	assert rig.cache.put_calls == []


def test_given_real_size_over_cap_when_preview_kind_then_too_large_without_pull() -> None:
	# given
	rig = _Rig()
	rig.devices.stat_entries[PATH] = DeviceEntry("PANO_0042.jpg", False, size=40 * MEGABYTE)
	# when
	kind = _error_kind(rig, _request(kind=DevicePreviewKind.PREVIEW, size=1_000))
	# then
	assert kind is DevicePreviewErrorKind.TOO_LARGE
	assert rig.devices.pull_timeout_calls == []


def test_given_pull_fails_when_thumb_then_error_mapped_and_temp_deleted() -> None:
	# given
	rig = _Rig()
	rig.devices.stat_entries[PATH] = DeviceEntry("IMG_0001.jpg", False, size=1000)
	rig.devices.pull_errors[PATH] = DeviceBrowseErrorKind.TIMEOUT
	# when
	kind = _error_kind(rig, _request())
	# then
	assert kind is DevicePreviewErrorKind.TIMEOUT
	assert rig.filesystem.temp_files_created
	assert not (set(rig.filesystem.temp_files_created) & set(rig.filesystem.files))
	assert rig.imaging.render_calls == []
	assert rig.cache.put_calls == []


def test_given_render_fails_when_thumb_then_error_propagates_temp_deleted_and_nothing_cached() -> None:
	# given
	rig = _Rig()
	rig.devices.stat_entries[PATH] = DeviceEntry("IMG_0001.jpg", False, size=1000)
	rig.imaging.render_error = DevicePreviewErrorKind.NO_PREVIEW
	# when
	kind = _error_kind(rig, _request())
	# then
	assert kind is DevicePreviewErrorKind.NO_PREVIEW
	assert not (set(rig.filesystem.temp_files_created) & set(rig.filesystem.files))
	assert rig.cache.put_calls == []


def test_given_cache_hit_when_thumb_then_served_without_any_device_call() -> None:
	# given
	rig = _Rig()
	request = _request()
	key = device_preview_cache_key(request)
	rig.cache.store[key] = CachedDevicePreview(b"cached-jpeg")
	# when
	preview = rig.use_case(request)
	# then
	assert preview.jpeg == b"cached-jpeg"
	assert key in preview.etag
	assert rig.devices.device_calls == 0
	assert rig.filesystem.temp_files_created == []
	assert rig.cache.put_calls == []


def test_given_changed_size_when_cached_entry_for_old_size_then_regenerated_from_phone() -> None:
	# given
	rig = _Rig()
	rig.cache.store[device_preview_cache_key(_request(size=800_000))] = CachedDevicePreview(b"old")
	rig.devices.heads[PATH] = b"head"
	rig.imaging.embedded = b"fresh"
	# when
	preview = rig.use_case(_request(size=900_000))
	# then
	assert preview.jpeg == b"fresh"
	assert len(rig.devices.read_head_calls) == 1


def test_given_busy_device_when_thumb_then_device_busy_without_device_calls() -> None:
	# given
	rig = _Rig()
	rig.activity.busy = True
	# when
	kind = _error_kind(rig, _request())
	# then
	assert kind is DevicePreviewErrorKind.DEVICE_BUSY
	assert rig.activity.calls == [(ConnectionMethod.ADB, "dev1")]
	assert rig.devices.device_calls == 0


def test_given_busy_device_when_cache_hit_then_still_served_because_no_device_call() -> None:
	# given
	rig = _Rig()
	rig.activity.busy = True
	request = _request()
	rig.cache.store[device_preview_cache_key(request)] = CachedDevicePreview(b"cached-jpeg")
	# when
	preview = rig.use_case(request)
	# then
	assert preview.jpeg == b"cached-jpeg"
	assert rig.devices.device_calls == 0


@pytest.mark.parametrize(
	("failure", "expected"),
	[
		(DeviceBrowseErrorKind.UNPLUGGED, DevicePreviewErrorKind.UNPLUGGED),
		(DeviceBrowseErrorKind.UNAUTHORIZED, DevicePreviewErrorKind.UNAUTHORIZED),
		(DeviceBrowseErrorKind.TIMEOUT, DevicePreviewErrorKind.TIMEOUT),
		(DeviceBrowseErrorKind.NOT_FOUND, DevicePreviewErrorKind.NO_PREVIEW),
	],
)
def test_given_head_read_fails_when_thumb_then_browse_error_mapped(
	failure: DeviceBrowseErrorKind, expected: DevicePreviewErrorKind
) -> None:
	# given
	rig = _Rig()
	rig.devices.head_errors[PATH] = failure
	# when
	kind = _error_kind(rig, _request())
	# then
	assert kind is expected
	assert rig.cache.put_calls == []


@pytest.mark.parametrize(
	("failure", "expected"),
	[
		(DeviceBrowseErrorKind.UNPLUGGED, DevicePreviewErrorKind.UNPLUGGED),
		(DeviceBrowseErrorKind.UNAUTHORIZED, DevicePreviewErrorKind.UNAUTHORIZED),
		(DeviceBrowseErrorKind.TIMEOUT, DevicePreviewErrorKind.TIMEOUT),
		(DeviceBrowseErrorKind.NOT_FOUND, DevicePreviewErrorKind.NO_PREVIEW),
	],
)
def test_given_stat_fails_when_preview_then_browse_error_mapped(
	failure: DeviceBrowseErrorKind, expected: DevicePreviewErrorKind
) -> None:
	# given
	rig = _Rig()
	rig.devices.stat_errors[PATH] = failure
	# when
	kind = _error_kind(rig, _request(kind=DevicePreviewKind.PREVIEW))
	# then
	assert kind is expected


def test_given_path_is_a_folder_when_preview_then_no_preview() -> None:
	# given
	rig = _Rig()
	rig.devices.stat_entries[PATH] = DeviceEntry("IMG_0001.jpg", True)
	# when
	kind = _error_kind(rig, _request(kind=DevicePreviewKind.PREVIEW))
	# then
	assert kind is DevicePreviewErrorKind.NO_PREVIEW
	assert rig.devices.pull_timeout_calls == []


@pytest.mark.parametrize("path", ["DCIM/Camera/clip.avi", "DCIM/Camera/IMG_0001.cr2", "DCIM/Camera/README", "DCIM"])
def test_given_non_image_extension_when_thumb_then_no_preview_without_device_calls(path: str) -> None:
	# given
	rig = _Rig()
	# when
	kind = _error_kind(rig, _request(path=path))
	# then
	assert kind is DevicePreviewErrorKind.NO_PREVIEW
	assert rig.devices.device_calls == 0
	assert rig.activity.calls == []


@pytest.mark.parametrize("path", ["DCIM/../Android/data/x.jpg", "../x.jpg", "DCIM\\..\\x.jpg", "DCIM/a\x00.jpg"])
def test_given_invalid_path_when_thumb_then_invalid_path_without_device_calls(path: str) -> None:
	# given
	rig = _Rig()
	# when
	kind = _error_kind(rig, _request(path=path))
	# then
	assert kind is DevicePreviewErrorKind.INVALID_PATH
	assert rig.devices.device_calls == 0
	assert rig.cache.get_calls == []


def test_given_sdcard_prefixed_path_when_thumb_then_device_gets_storage_relative_path() -> None:
	# given
	rig = _Rig()
	rig.imaging.embedded = b"embedded-jpeg"
	# when
	rig.use_case(_request(path="/sdcard/DCIM/Camera/IMG_0001.jpg"))
	# then
	assert [call[1] for call in rig.devices.read_head_calls] == ["DCIM/Camera/IMG_0001.jpg"]


@pytest.mark.parametrize("alias", ["DCIM/x.jpg", "/storage/emulated/0/DCIM/x.jpg"])
def test_given_preview_generated_for_sdcard_path_when_same_file_by_other_spelling_then_cache_hit_same_etag(
	alias: str,
) -> None:
	# given
	rig = _Rig()
	rig.imaging.embedded = b"embedded-jpeg"
	first = rig.use_case(_request(path="/sdcard/DCIM/x.jpg"))
	calls_after_first = rig.devices.device_calls
	# when
	second = rig.use_case(_request(path=alias))
	# then
	assert second.jpeg == b"embedded-jpeg"
	assert second.etag == first.etag
	assert rig.devices.device_calls == calls_after_first
	assert len(rig.cache.put_calls) == 1


def test_given_preview_kind_when_get_then_no_head_read_and_renders_1600() -> None:
	# given
	rig = _Rig()
	rig.devices.stat_entries[PATH] = DeviceEntry("IMG_0001.jpg", False, size=4 * MEGABYTE)
	rig.imaging.embedded = b"never-used"
	rig.imaging.rendered = b"rendered-1600"
	request = _request(kind=DevicePreviewKind.PREVIEW)
	# when
	preview = rig.use_case(request)
	# then
	assert preview.jpeg == b"rendered-1600"
	assert rig.devices.read_head_calls == []
	assert rig.imaging.head_calls == []
	temp = rig.filesystem.temp_files_created[0]
	assert rig.imaging.render_calls == [(temp, 1600, PREVIEW_FULL_TIMEOUT_S)]
	assert temp not in rig.filesystem.files
	assert rig.cache.put_calls == [(device_preview_cache_key(request), CachedDevicePreview(b"rendered-1600"))]


def test_given_afc_method_when_get_then_repository_resolved_for_that_method() -> None:
	# given
	rig = _Rig()
	rig.imaging.embedded = b"embedded-jpeg"
	request = replace(_request(), method=ConnectionMethod.AFC)
	# when
	rig.use_case(request)
	# then
	assert rig.resolved == [ConnectionMethod.AFC]
	assert rig.activity.calls == [(ConnectionMethod.AFC, "dev1")]


def test_given_cap_reached_on_one_device_when_more_requests_then_at_most_cap_run_and_other_device_unblocked() -> None:
	# given
	rig = _Rig()
	rig.imaging.embedded = b"embedded-jpeg"
	gate = threading.Event()
	rig.devices.head_gates["slow"] = gate
	paths = [f"DCIM/IMG_{i}.jpg" for i in range(PREVIEW_MAX_CONCURRENT_READS + 1)]
	pool = ThreadPoolExecutor(max_workers=PREVIEW_MAX_CONCURRENT_READS + 3)
	try:
		blocked = [pool.submit(rig.use_case, _request(path=p, device_id="slow")) for p in paths]
		for _ in range(PREVIEW_MAX_CONCURRENT_READS):
			assert rig.devices.head_entered.acquire(timeout=2)
		# when
		other = pool.submit(rig.use_case, _request(device_id="fast")).result(timeout=2)
		assert rig.devices.head_entered.acquire(timeout=2)  # the "fast" read's own entry
		# then
		assert other.jpeg == b"embedded-jpeg"
		assert rig.devices.active_heads["slow"] == PREVIEW_MAX_CONCURRENT_READS
		gate.set()
		for future in blocked:
			assert future.result(timeout=2).jpeg == b"embedded-jpeg"
		assert rig.devices.peak_heads["slow"] == PREVIEW_MAX_CONCURRENT_READS
	finally:
		gate.set()
		pool.shutdown(wait=True)


# RAW (DNG) previews

DNG_PATH = "DCIM/Camera/PXL_20260305_203512870.RAW-02.ORIGINAL.dng"
PREVIEW_AT = 6000


def _serve_dng(rig: _Rig, dng: DngFile, path: str = DNG_PATH, size: int | None = None) -> None:
	rig.devices.heads[path] = dng.head
	rig.devices.range_data[path] = dng.data
	rig.devices.stat_entries[path] = DeviceEntry(path.rsplit("/", 1)[-1], False, size=size or dng.size, mtime=1)


def _pixel_dng(ifd0_at: int = 8, orientation: int = 6) -> DngFile:
	entries = jpeg_ifd(1280, 960, PREVIEW_AT, len(JPEG), orientation=orientation)
	return build_dng("<", [(ifd0_at, entries)], jpeg_at=PREVIEW_AT)


def test_given_pixel_dng_when_thumb_then_header_read_then_only_preview_range_and_cached() -> None:
	# given
	rig = _Rig()
	_serve_dng(rig, _pixel_dng())
	request = _request(path=DNG_PATH)
	# when
	preview = rig.use_case(request)
	# then
	assert preview.jpeg == b"rendered-embedded-jpeg"
	assert rig.devices.read_head_calls == [("dev1", DNG_PATH, DNG_HEADER_READ_BYTES, DNG_HEADER_TIMEOUT_S)]
	assert rig.devices.read_range_calls == [("dev1", DNG_PATH, PREVIEW_AT, len(JPEG), DNG_PREVIEW_TIMEOUT_S)]
	assert rig.devices.pull_timeout_calls == []
	assert rig.imaging.render_embedded_calls == [(JPEG, 320, 6, PREVIEW_FULL_TIMEOUT_S)]
	assert rig.imaging.render_calls == []
	key = device_preview_cache_key(request)
	assert rig.cache.put_calls == [(key, CachedDevicePreview(b"rendered-embedded-jpeg"))]


def test_given_dng_when_preview_kind_then_renders_1600() -> None:
	# given
	rig = _Rig()
	_serve_dng(rig, _pixel_dng())
	# when
	rig.use_case(_request(path=DNG_PATH, kind=DevicePreviewKind.PREVIEW))
	# then
	assert rig.imaging.render_embedded_calls[0][1] == 1600


def test_given_ifd0_near_end_when_thumb_then_one_extra_header_range_read_before_preview() -> None:
	# given
	rig = _Rig()
	_serve_dng(rig, _pixel_dng(ifd0_at=20_000))
	# when
	rig.use_case(_request(path=DNG_PATH))
	# then
	calls = [(offset, length) for _, _, offset, length, _ in rig.devices.read_range_calls]
	assert calls[0][0] == 20_000
	assert calls[1] == (PREVIEW_AT, len(JPEG))
	assert len(calls) == 2
	assert rig.devices.read_range_calls[0][4] == DNG_HEADER_TIMEOUT_S


def test_given_52_mb_dng_when_thumb_then_never_too_large_and_never_pulled() -> None:
	# given
	rig = _Rig()
	_serve_dng(rig, _pixel_dng(), size=52 * MEGABYTE)
	# when
	preview = rig.use_case(_request(path=DNG_PATH))
	# then
	assert preview.jpeg == b"rendered-embedded-jpeg"
	assert rig.devices.pull_timeout_calls == []


def test_given_jpeg_bytes_with_dng_name_when_thumb_then_photo_strategy_with_jpg_temp_suffix() -> None:
	# given
	rig = _Rig()
	path = "Pictures/Snapseed/12427.dng"
	rig.devices.heads[path] = b"\xff\xd8\xff\xe1exif"
	rig.devices.stat_entries[path] = DeviceEntry("12427.dng", False, size=800_000, mtime=1)
	rig.imaging.rendered = b"photo-320"
	# when
	preview = rig.use_case(_request(path=path))
	# then
	assert preview.jpeg == b"photo-320"
	assert rig.imaging.head_calls  # EXIF thumbnail was tried from the head
	assert rig.filesystem.temp_files_created[0].endswith(".jpg")
	assert rig.devices.read_range_calls == []
	assert rig.imaging.render_embedded_calls == []


def test_given_jpeg_bytes_with_dng_name_and_embedded_thumbnail_when_thumb_then_uses_it() -> None:
	# given
	rig = _Rig()
	path = "Pictures/Snapseed/12427.DNG"
	rig.devices.heads[path] = b"\xff\xd8\xff\xe1exif"
	rig.imaging.embedded = b"embedded"
	# when
	preview = rig.use_case(_request(path=path))
	# then
	assert preview.jpeg == b"embedded"
	assert rig.devices.pull_timeout_calls == []


def test_given_jpeg_bytes_with_dng_name_over_25_mb_when_preview_then_too_large() -> None:
	# given
	rig = _Rig()
	path = "Pictures/Snapseed/12427.dng"
	rig.devices.heads[path] = b"\xff\xd8\xff\xe1exif"
	rig.devices.stat_entries[path] = DeviceEntry("12427.dng", False, size=PREVIEW_FULL_PULL_MAX_BYTES + 1, mtime=1)
	# when
	kind = _error_kind(rig, _request(path=path, kind=DevicePreviewKind.PREVIEW))
	# then
	assert kind is DevicePreviewErrorKind.TOO_LARGE


def test_given_lightroom_proxy_when_thumb_then_no_preview_after_header_reads_only() -> None:
	# given
	rig = _Rig()
	entries = jpeg_ifd(1280, 960, PREVIEW_AT, len(JPEG), compression=52546)
	_serve_dng(rig, build_dng("<", [(8, entries)], jpeg_at=PREVIEW_AT), path="Pictures/x_proxy.dng")
	# when
	kind = _error_kind(rig, _request(path="Pictures/x_proxy.dng"))
	# then
	assert kind is DevicePreviewErrorKind.NO_PREVIEW
	assert rig.devices.read_range_calls == []
	assert rig.imaging.render_embedded_calls == []
	assert rig.cache.put_calls == []


def test_given_neither_jpeg_nor_tiff_when_thumb_then_no_preview_after_first_read() -> None:
	# given
	rig = _Rig()
	rig.devices.heads[DNG_PATH] = b"RIFF....WEBP"
	# when
	kind = _error_kind(rig, _request(path=DNG_PATH))
	# then
	assert kind is DevicePreviewErrorKind.NO_PREVIEW
	assert len(rig.devices.read_head_calls) == 1
	assert rig.devices.stat_calls == []
	assert rig.devices.read_range_calls == []


def test_given_short_preview_read_when_thumb_then_no_preview() -> None:
	# given
	rig = _Rig()
	dng = _pixel_dng()
	_serve_dng(rig, dng)
	rig.devices.range_data[DNG_PATH] = dng.data[: PREVIEW_AT + 5]
	# when
	kind = _error_kind(rig, _request(path=DNG_PATH))
	# then
	assert kind is DevicePreviewErrorKind.NO_PREVIEW
	assert rig.imaging.render_embedded_calls == []


def test_given_preview_bytes_not_jpeg_when_thumb_then_no_preview() -> None:
	# given
	rig = _Rig()
	dng = _pixel_dng()
	_serve_dng(rig, dng)
	data = bytearray(dng.data)
	data[PREVIEW_AT : PREVIEW_AT + 2] = b"XX"
	rig.devices.range_data[DNG_PATH] = bytes(data)
	# when
	kind = _error_kind(rig, _request(path=DNG_PATH))
	# then
	assert kind is DevicePreviewErrorKind.NO_PREVIEW


def test_given_dng_path_is_a_folder_when_thumb_then_no_preview() -> None:
	# given
	rig = _Rig()
	dng = _pixel_dng()
	_serve_dng(rig, dng)
	rig.devices.stat_entries[DNG_PATH] = DeviceEntry("x.dng", True)
	# when
	kind = _error_kind(rig, _request(path=DNG_PATH))
	# then
	assert kind is DevicePreviewErrorKind.NO_PREVIEW


def test_given_busy_device_when_dng_thumb_then_device_busy_without_device_calls() -> None:
	# given
	rig = _Rig()
	_serve_dng(rig, _pixel_dng())
	rig.activity.busy = True
	# when
	kind = _error_kind(rig, _request(path=DNG_PATH))
	# then
	assert kind is DevicePreviewErrorKind.DEVICE_BUSY
	assert rig.devices.device_calls == 0


def test_given_cached_dng_when_thumb_then_no_device_call() -> None:
	# given
	rig = _Rig()
	request = _request(path=DNG_PATH)
	rig.cache.put(device_preview_cache_key(request), CachedDevicePreview(b"cached"))
	# when
	preview = rig.use_case(request)
	# then
	assert preview.jpeg == b"cached"
	assert rig.devices.device_calls == 0


def test_given_range_read_fails_when_dng_thumb_then_browse_error_mapped() -> None:
	# given
	rig = _Rig()
	_serve_dng(rig, _pixel_dng())
	rig.devices.range_errors[DNG_PATH] = DeviceBrowseErrorKind.UNPLUGGED
	# when
	kind = _error_kind(rig, _request(path=DNG_PATH))
	# then
	assert kind is DevicePreviewErrorKind.UNPLUGGED


def test_given_iphone_prores_dng_over_afc_when_thumb_then_embedded_preview_via_afc_repository() -> None:
	# given
	rig = _Rig()
	path = "DCIM/100APPLE/IMG_1002.DNG"
	entries = jpeg_ifd(3088, 2316, PREVIEW_AT, len(JPEG), orientation=6)
	_serve_dng(rig, build_dng(">", [(18, entries)], jpeg_at=PREVIEW_AT), path=path)
	request = replace(_request(path=path), method=ConnectionMethod.AFC)
	# when
	preview = rig.use_case(request)
	# then
	assert preview.jpeg == b"rendered-embedded-jpeg"
	assert rig.resolved == [ConnectionMethod.AFC]
	assert rig.devices.read_range_calls == [("dev1", path, PREVIEW_AT, len(JPEG), DNG_PREVIEW_TIMEOUT_S)]
	assert rig.imaging.render_embedded_calls == [(JPEG, 320, 6, PREVIEW_FULL_TIMEOUT_S)]


def test_given_cap_reached_with_dngs_when_more_requests_then_at_most_cap_read_at_once() -> None:
	# given
	rig = _Rig()
	gate = threading.Event()
	rig.devices.head_gates["slow"] = gate
	paths = [f"DCIM/Camera/PXL_{i}.RAW-02.ORIGINAL.dng" for i in range(PREVIEW_MAX_CONCURRENT_READS + 1)]
	for path in paths:
		_serve_dng(rig, _pixel_dng(), path=path)
	pool = ThreadPoolExecutor(max_workers=PREVIEW_MAX_CONCURRENT_READS + 1)
	try:
		# when
		futures = [pool.submit(rig.use_case, _request(path=p, device_id="slow")) for p in paths]
		for _ in range(PREVIEW_MAX_CONCURRENT_READS):
			assert rig.devices.head_entered.acquire(timeout=2)
		# then
		assert not rig.devices.head_entered.acquire(timeout=0.2)
		assert rig.devices.active_heads["slow"] == PREVIEW_MAX_CONCURRENT_READS
		gate.set()
		for future in futures:
			assert future.result(timeout=2).jpeg == b"rendered-embedded-jpeg"
		assert rig.devices.peak_heads["slow"] == PREVIEW_MAX_CONCURRENT_READS
	finally:
		gate.set()
		pool.shutdown(wait=True)
