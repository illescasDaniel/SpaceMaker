import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace

import pytest
from tests.unit.fakes import (
	FakeDeviceActivity,
	FakeDevicePreviewCache,
	FakeDeviceRepository,
	FakeFileSystem,
	FakePreviewImaging,
)

from spacemaker.application.get_device_preview import GetDevicePreview
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.device_browse import DeviceBrowseErrorKind, DeviceEntry
from spacemaker.domain.device_preview import (
	PREVIEW_FULL_PULL_MAX_BYTES,
	PREVIEW_FULL_TIMEOUT_S,
	PREVIEW_HEAD_BYTES,
	PREVIEW_HEAD_TIMEOUT_S,
	PREVIEW_MAX_CONCURRENT_READS,
	DevicePreviewError,
	DevicePreviewErrorKind,
	DevicePreviewKind,
	DevicePreviewRequest,
	device_preview_cache_key,
)


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
		self.use_case = GetDevicePreview(self._resolve, self.cache, self.imaging, self.activity, self.filesystem)

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
	assert rig.cache.put_calls == [(key, b"embedded-jpeg")]
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
	assert rig.cache.put_calls == [(device_preview_cache_key(_request()), b"rendered-320")]


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
	rig.cache.store[key] = b"cached-jpeg"
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
	rig.cache.store[device_preview_cache_key(_request(size=800_000))] = b"old"
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
	rig.cache.store[device_preview_cache_key(request)] = b"cached-jpeg"
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


@pytest.mark.parametrize("path", ["DCIM/Camera/clip.mp4", "DCIM/Camera/IMG_0001.dng", "DCIM/Camera/README", "DCIM"])
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
	assert rig.cache.put_calls == [(device_preview_cache_key(request), b"rendered-1600")]


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
