# Video posters, GetDevicePreview video branch (SPEC "Video posters" strategy / failure handling / budget /
# trust boundary and the "Video posters — request lifecycle" and "busy device" scenarios):
#   cache miss -> stat -> token minted for the real size -> poster renders from stream_url(token) with the
#   kind's max_edge and VIDEO_POSTER_TIMEOUT_S -> JPEG + duration cached -> token revoked (every outcome);
#   cache hit -> stored duration, no device call / poster run; videos are never TOO_LARGE; busy -> DEVICE_BUSY
#   before any work; one shared slot pool with photos; unknown duration -> None; failures cache nothing.
import re
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field, replace

import pytest
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
	PREVIEW_MAX_CONCURRENT_READS,
	VIDEO_POSTER_TIMEOUT_S,
	CachedDevicePreview,
	DevicePreview,
	DevicePreviewCancelled,
	DevicePreviewError,
	DevicePreviewErrorKind,
	DevicePreviewKind,
	DevicePreviewRequest,
	VideoPoster,
	device_preview_cache_key,
)
from spacemaker.domain.device_stream import DeviceStreamGrant


PATH = "DCIM/Camera/VID_0001.mp4"
URL_PREFIX = "http://127.0.0.1:9/api/device/stream?token="
GIGABYTE = 1024**3


@dataclass
class _Rig:
	devices: FakeDeviceRepository = field(default_factory=FakeDeviceRepository)
	cache: FakeDevicePreviewCache = field(default_factory=FakeDevicePreviewCache)
	activity: FakeDeviceActivity = field(default_factory=FakeDeviceActivity)
	filesystem: FakeFileSystem = field(default_factory=FakeFileSystem)
	poster: FakeVideoPoster = field(default_factory=FakeVideoPoster)
	tokens: DeviceStreamTokens = field(default_factory=DeviceStreamTokens)
	seen_grants: list[DeviceStreamGrant | None] = field(default_factory=list)
	resolved: list[ConnectionMethod] = field(default_factory=list)
	slot_wait_s: float = 20.0
	slot_poll_s: float = 0.25
	clock: Callable[[], float] = time.monotonic

	def __post_init__(self) -> None:
		self.devices.bind_filesystem(self.filesystem)
		self.devices.stat_entries[PATH] = DeviceEntry("VID_0001.mp4", False, size=90_000_000, mtime=1)
		self.imaging = FakePreviewImaging(filesystem=self.filesystem)
		self.poster.on_render = self._observe
		self.use_case = GetDevicePreview(
			self._resolve,
			self.cache,
			self.imaging,
			self.activity,
			self.filesystem,
			poster=self.poster,
			tokens=self.tokens,
			stream_url=lambda token: f"{URL_PREFIX}{token}",
			slot_wait_s=self.slot_wait_s,
			slot_poll_s=self.slot_poll_s,
			clock=self.clock,
		)

	def _resolve(self, method: ConnectionMethod) -> FakeDeviceRepository:
		self.resolved.append(method)
		return self.devices

	def _observe(self, url: str) -> None:
		"""Runs inside the poster: what the token allows while ffmpeg would be reading."""
		self.seen_grants.append(self.tokens.resolve(_token_of(url)))

	def tokens_used(self) -> list[str]:
		return [_token_of(call[0]) for call in self.poster.calls]


def _token_of(url: str) -> str:
	match = re.fullmatch(re.escape(URL_PREFIX) + r"(.+)", url)
	assert match is not None
	return match.group(1)


def _request(
	path: str = PATH,
	kind: DevicePreviewKind = DevicePreviewKind.THUMB,
	size: int = 90_000_000,
	device_id: str = "dev1",
) -> DevicePreviewRequest:
	return DevicePreviewRequest(ConnectionMethod.ADB, device_id, path, size, 1_700_000_000, kind)


def _error_kind(rig: _Rig, request: DevicePreviewRequest) -> DevicePreviewErrorKind:
	with pytest.raises(DevicePreviewError) as raised:
		rig.use_case(request)
	return raised.value.kind


def test_given_cache_miss_when_thumb_then_stat_token_poster_320_with_timeout_and_jpeg_plus_duration_cached() -> None:
	# given
	rig = _Rig()
	request = _request()
	# when
	preview = rig.use_case(request)
	# then
	assert preview.jpeg == b"poster-jpeg"
	assert preview.duration_s == 42.37
	assert rig.devices.stat_calls == [PATH]
	assert len(rig.poster.calls) == 1
	url, max_edge, timeout_s = rig.poster.calls[0]
	assert url.startswith(URL_PREFIX)
	assert (max_edge, timeout_s) == (320, VIDEO_POSTER_TIMEOUT_S)
	key = device_preview_cache_key(request)
	assert rig.cache.put_calls == [(key, CachedDevicePreview(b"poster-jpeg", 42.37))]
	assert key in preview.etag


def test_given_preview_kind_when_video_then_poster_rendered_at_1600() -> None:
	# given
	rig = _Rig()
	# when
	rig.use_case(_request(kind=DevicePreviewKind.PREVIEW))
	# then
	assert rig.poster.calls[0][1] == 1600


def test_given_video_when_generated_then_no_head_read_no_pull_no_temp_file_no_imaging() -> None:
	# given
	rig = _Rig()
	# when
	rig.use_case(_request())
	# then
	assert rig.devices.read_head_calls == []
	assert rig.devices.pull_timeout_calls == []
	assert rig.filesystem.temp_files_created == []
	assert rig.imaging.head_calls == []
	assert rig.imaging.render_calls == []


def test_given_client_lies_about_size_when_video_then_token_bound_to_real_size_and_normalized_path() -> None:
	# given
	rig = _Rig()
	request = _request(path=f"/sdcard/{PATH}", size=1)
	# when
	rig.use_case(request)
	# then
	assert rig.seen_grants == [DeviceStreamGrant(ConnectionMethod.ADB, "dev1", PATH, 90_000_000)]


def test_given_success_when_video_then_token_alive_during_render_and_revoked_after() -> None:
	# given
	rig = _Rig()
	# when
	rig.use_case(_request())
	# then
	assert rig.seen_grants[0] is not None
	assert rig.tokens.resolve(rig.tokens_used()[0]) is None


@pytest.mark.parametrize(
	"failure",
	[
		DevicePreviewErrorKind.TIMEOUT,
		DevicePreviewErrorKind.NO_PREVIEW,
		DevicePreviewErrorKind.DEVICE_BUSY,
		DevicePreviewErrorKind.UNPLUGGED,
	],
)
def test_given_poster_fails_when_video_then_error_propagates_token_revoked_and_nothing_cached(
	failure: DevicePreviewErrorKind,
) -> None:
	# given
	rig = _Rig()
	rig.poster.error = failure
	# when
	kind = _error_kind(rig, _request())
	# then
	assert kind is failure
	assert rig.cache.put_calls == []
	assert rig.tokens.resolve(rig.tokens_used()[0]) is None


@pytest.mark.parametrize(
	("failure", "expected"),
	[
		(DeviceBrowseErrorKind.UNPLUGGED, DevicePreviewErrorKind.UNPLUGGED),
		(DeviceBrowseErrorKind.UNAUTHORIZED, DevicePreviewErrorKind.UNAUTHORIZED),
		(DeviceBrowseErrorKind.TIMEOUT, DevicePreviewErrorKind.TIMEOUT),
		(DeviceBrowseErrorKind.NOT_FOUND, DevicePreviewErrorKind.NO_PREVIEW),
	],
)
def test_given_stat_fails_when_video_then_mapped_without_token_or_poster(
	failure: DeviceBrowseErrorKind, expected: DevicePreviewErrorKind
) -> None:
	# given
	rig = _Rig()
	rig.devices.stat_errors[PATH] = failure
	# when
	kind = _error_kind(rig, _request())
	# then
	assert kind is expected
	assert rig.poster.calls == []
	assert rig.cache.put_calls == []


def test_given_path_is_a_folder_when_video_then_no_preview_without_poster() -> None:
	# given
	rig = _Rig()
	rig.devices.stat_entries[PATH] = DeviceEntry("VID_0001.mp4", True)
	# when
	kind = _error_kind(rig, _request())
	# then
	assert kind is DevicePreviewErrorKind.NO_PREVIEW
	assert rig.poster.calls == []


@pytest.mark.parametrize("kind", [DevicePreviewKind.THUMB, DevicePreviewKind.PREVIEW])
def test_given_huge_video_when_requested_then_never_too_large(kind: DevicePreviewKind) -> None:
	# given
	rig = _Rig()
	rig.devices.stat_entries[PATH] = DeviceEntry("VID_0001.mp4", False, size=8 * GIGABYTE)
	# when
	preview = rig.use_case(_request(kind=kind, size=1_000))
	# then
	assert preview.jpeg == b"poster-jpeg"
	assert len(rig.poster.calls) == 1


def test_given_cache_hit_when_video_then_stored_duration_and_no_device_call_or_poster() -> None:
	# given
	rig = _Rig()
	request = _request()
	rig.cache.store[device_preview_cache_key(request)] = CachedDevicePreview(b"cached-poster", 12.5)
	# when
	preview = rig.use_case(request)
	# then
	assert (preview.jpeg, preview.duration_s) == (b"cached-poster", 12.5)
	assert rig.devices.device_calls == 0
	assert rig.poster.calls == []
	assert rig.activity.calls == []
	assert rig.cache.put_calls == []


def test_given_busy_device_when_video_then_device_busy_before_any_work() -> None:
	# given
	rig = _Rig()
	rig.activity.busy = True
	# when
	kind = _error_kind(rig, _request())
	# then
	assert kind is DevicePreviewErrorKind.DEVICE_BUSY
	assert rig.devices.device_calls == 0
	assert rig.poster.calls == []


def test_given_busy_device_when_cache_hit_video_then_still_served() -> None:
	# given
	rig = _Rig()
	rig.activity.busy = True
	request = _request()
	rig.cache.store[device_preview_cache_key(request)] = CachedDevicePreview(b"cached-poster", 3.0)
	# when
	preview = rig.use_case(request)
	# then
	assert preview.jpeg == b"cached-poster"


def test_given_duration_unknown_when_video_then_none_in_response_and_in_cache() -> None:
	# given
	rig = _Rig()
	rig.poster.poster = VideoPoster(b"poster-jpeg", None)
	request = _request()
	# when
	preview = rig.use_case(request)
	# then
	assert preview.duration_s is None
	assert rig.cache.put_calls == [(device_preview_cache_key(request), CachedDevicePreview(b"poster-jpeg", None))]


def test_given_uppercase_video_extension_when_thumb_then_video_pipeline() -> None:
	# given
	rig = _Rig()
	path = "DCIM/Camera/VID_0002.MOV"
	rig.devices.stat_entries[path] = DeviceEntry("VID_0002.MOV", False, size=5_000)
	# when
	rig.use_case(_request(path=path))
	# then
	assert len(rig.poster.calls) == 1
	assert rig.devices.read_head_calls == []


def test_given_afc_method_when_video_then_repository_resolved_for_that_method() -> None:
	# given
	rig = _Rig()
	request = replace(_request(), method=ConnectionMethod.AFC)
	# when
	rig.use_case(request)
	# then
	assert rig.resolved == [ConnectionMethod.AFC]
	assert rig.seen_grants[0] is not None
	assert rig.seen_grants[0].method is ConnectionMethod.AFC


def test_given_two_requests_when_video_then_each_gets_its_own_token() -> None:
	# given
	rig = _Rig()
	rig.devices.stat_entries["b.mp4"] = DeviceEntry("b.mp4", False, size=10)
	# when
	rig.use_case(_request())
	rig.use_case(_request(path="b.mp4"))
	# then
	first, second = rig.tokens_used()
	assert first != second


class _Concurrency:
	"""Counts how many device reads (photo heads and video renders alike) are in flight at once."""

	def __init__(self) -> None:
		self.active = 0
		self.peak = 0
		self.entered = threading.Semaphore(0)
		self._lock = threading.Lock()

	def enter(self) -> None:
		with self._lock:
			self.active += 1
			self.peak = max(self.peak, self.active)
		self.entered.release()

	def leave(self) -> None:
		with self._lock:
			self.active -= 1


class _TrackedRepository(FakeDeviceRepository):
	def __init__(self, tracker: _Concurrency, gate: threading.Event) -> None:
		super().__init__()
		self.tracker = tracker
		self.gate = gate

	def read_head(self, device_id: str, path: str, max_bytes: int, timeout_s: float) -> bytes:
		self.tracker.enter()
		try:
			self.gate.wait(timeout=5)
			return super().read_head(device_id, path, max_bytes, timeout_s)
		finally:
			self.tracker.leave()


class _TrackedPoster(FakeVideoPoster):
	def __init__(self, tracker: _Concurrency) -> None:
		super().__init__()
		self.tracker = tracker

	def render_poster(
		self, source_url: str, max_edge: int, timeout_s: float, cancel: threading.Event | None = None
	) -> VideoPoster:
		self.tracker.enter()
		try:
			return super().render_poster(source_url, max_edge, timeout_s, cancel)
		finally:
			self.tracker.leave()


def test_given_more_videos_and_photos_than_slots_when_requested_then_at_most_cap_reads_run_at_once() -> None:
	# given
	tracker = _Concurrency()
	gate = threading.Event()
	filesystem = FakeFileSystem()
	devices = _TrackedRepository(tracker, gate)
	devices.bind_filesystem(filesystem)
	poster = _TrackedPoster(tracker)
	poster.gate = gate
	imaging = FakePreviewImaging(filesystem=filesystem, embedded=b"embedded-jpeg")
	use_case = GetDevicePreview(
		lambda _method: devices,
		FakeDevicePreviewCache(),
		imaging,
		FakeDeviceActivity(),
		filesystem,
		poster=poster,
		tokens=DeviceStreamTokens(),
		stream_url=lambda token: f"{URL_PREFIX}{token}",
	)
	total = PREVIEW_MAX_CONCURRENT_READS * 2
	paths = [f"DCIM/{i}.mp4" if i % 2 == 0 else f"DCIM/{i}.jpg" for i in range(total)]
	for path in paths:
		devices.stat_entries[path] = DeviceEntry(path, False, size=1000)
	pool = ThreadPoolExecutor(max_workers=total)
	try:
		# when
		futures = [pool.submit(use_case, _request(path=path, device_id="slow")) for path in paths]
		for _ in range(PREVIEW_MAX_CONCURRENT_READS):
			assert tracker.entered.acquire(timeout=5)
		gate.set()
		results = [future.result(timeout=5) for future in futures]
		# then
		assert len(results) == total
		assert tracker.peak <= PREVIEW_MAX_CONCURRENT_READS
	finally:
		gate.set()
		pool.shutdown(wait=True)


def test_given_cancel_event_when_video_then_it_reaches_the_poster() -> None:
	# given
	rig = _Rig()
	cancel = threading.Event()
	# when
	rig.use_case(_request(), cancel=cancel)
	# then
	assert rig.poster.cancels == [cancel]


def test_given_cancel_set_during_render_when_video_then_cancelled_nothing_cached_and_token_revoked() -> None:
	# given
	rig = _Rig()
	cancel = threading.Event()
	rig.poster.on_render = lambda _url: cancel.set()
	# when
	with pytest.raises(DevicePreviewCancelled):
		rig.use_case(_request(), cancel=cancel)
	# then
	assert rig.cache.put_calls == []
	assert rig.tokens.resolve(rig.tokens_used()[0]) is None


def test_given_cancel_already_set_when_video_then_cancelled_before_any_device_work() -> None:
	# given
	rig = _Rig()
	cancel = threading.Event()
	cancel.set()
	# when
	with pytest.raises(DevicePreviewCancelled):
		rig.use_case(_request(), cancel=cancel)
	# then
	assert rig.devices.device_calls == 0
	assert rig.poster.calls == []
	assert rig.cache.put_calls == []


def _saturate_slots(rig: _Rig, pool: ThreadPoolExecutor, gate: threading.Event) -> list[Future[DevicePreview]]:
	rig.poster.gate = gate
	paths = [f"DCIM/V_{i}.mp4" for i in range(PREVIEW_MAX_CONCURRENT_READS)]
	for path in paths:
		rig.devices.stat_entries[path] = DeviceEntry(path, False, size=1000)
	holders = [pool.submit(rig.use_case, _request(path=path)) for path in paths]
	for _ in range(PREVIEW_MAX_CONCURRENT_READS):
		assert rig.poster.entered.acquire(timeout=5)
	return holders


def test_given_all_slots_held_when_wait_budget_elapses_then_timeout_without_device_work() -> None:
	# given
	ticks = iter(range(0, 1000, 10))  # fake clock: every look at it is 10 s later
	rig = _Rig(slot_wait_s=20.0, slot_poll_s=0.0, clock=lambda: float(next(ticks)))
	gate = threading.Event()
	pool = ThreadPoolExecutor(max_workers=PREVIEW_MAX_CONCURRENT_READS)
	try:
		holders = _saturate_slots(rig, pool, gate)
		# when
		kind = _error_kind(rig, _request(path="DCIM/waiting.mp4"))
		# then
		assert kind is DevicePreviewErrorKind.TIMEOUT
		assert len(rig.poster.calls) == PREVIEW_MAX_CONCURRENT_READS
		assert rig.cache.put_calls == []
		gate.set()
		for holder in holders:
			holder.result(timeout=5)
	finally:
		gate.set()
		pool.shutdown(wait=True)


def test_given_all_slots_held_when_cancel_set_while_waiting_then_cancelled_without_device_work() -> None:
	# given
	rig = _Rig(slot_wait_s=1e9, slot_poll_s=0.0)
	gate = threading.Event()
	cancel = threading.Event()
	pool = ThreadPoolExecutor(max_workers=PREVIEW_MAX_CONCURRENT_READS)
	try:
		holders = _saturate_slots(rig, pool, gate)
		cancel.set()
		# when
		with pytest.raises(DevicePreviewCancelled):
			rig.use_case(_request(path="DCIM/waiting.mp4"), cancel=cancel)
		# then
		assert len(rig.poster.calls) == PREVIEW_MAX_CONCURRENT_READS
		gate.set()
		for holder in holders:
			holder.result(timeout=5)
	finally:
		gate.set()
		pool.shutdown(wait=True)
