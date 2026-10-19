import pytest
from tests.unit.passcode_fakes import FakeClock

from spacemaker.application.device_listing_cache import DeviceListingCache, ListingKey
from spacemaker.domain.device_browse import DeviceBrowseError, DeviceBrowseErrorKind, DeviceEntry


class _Loader:
	def __init__(self, names: list[str] | None = None) -> None:
		self.calls = 0
		self.names = names or ["a"]

	def __call__(self) -> list[DeviceEntry]:
		self.calls += 1
		return [DeviceEntry(n, False) for n in self.names]


KEY: ListingKey = ("adb", "dev1", "DCIM")


def test_given_cached_listing_when_get_within_ttl_then_loader_called_once() -> None:
	# given
	clock = FakeClock()
	cache = DeviceListingCache(clock, ttl_seconds=30)
	loader = _Loader()
	cache.get_or_list(KEY, loader)
	clock.advance(29)
	# when
	again = cache.get_or_list(KEY, loader)
	# then
	assert loader.calls == 1
	assert [e.name for e in again] == ["a"]


def test_given_ttl_elapsed_when_get_then_reloaded() -> None:
	# given
	clock = FakeClock()
	cache = DeviceListingCache(clock, ttl_seconds=30)
	loader = _Loader()
	cache.get_or_list(KEY, loader)
	clock.advance(30.5)
	# when
	cache.get_or_list(KEY, loader)
	# then
	assert loader.calls == 2


def test_given_hits_when_reading_often_then_ttl_counts_from_load_time() -> None:
	# given
	clock = FakeClock()
	cache = DeviceListingCache(clock, ttl_seconds=30)
	loader = _Loader()
	cache.get_or_list(KEY, loader)
	clock.advance(20)
	cache.get_or_list(KEY, loader)
	clock.advance(20)
	# when
	cache.get_or_list(KEY, loader)
	# then
	assert loader.calls == 2


def test_given_cached_listing_when_refresh_then_reloaded_and_replaced() -> None:
	# given
	cache = DeviceListingCache(FakeClock())
	loader = _Loader(["old"])
	cache.get_or_list(KEY, loader)
	loader.names = ["new"]
	# when
	refreshed = cache.get_or_list(KEY, loader, refresh=True)
	after = cache.get_or_list(KEY, loader)
	# then
	assert [e.name for e in refreshed] == ["new"]
	assert [e.name for e in after] == ["new"]
	assert loader.calls == 2


def test_given_loader_error_when_get_then_propagates_and_not_cached() -> None:
	# given
	cache = DeviceListingCache(FakeClock())
	calls: list[int] = []

	def failing() -> list[DeviceEntry]:
		calls.append(1)
		raise DeviceBrowseError(DeviceBrowseErrorKind.TIMEOUT)

	# when
	with pytest.raises(DeviceBrowseError):
		cache.get_or_list(KEY, failing)
	ok = _Loader()
	cache.get_or_list(KEY, ok)
	# then
	assert len(calls) == 1
	assert ok.calls == 1


def test_given_returned_list_when_mutated_then_cache_unaffected() -> None:
	# given
	cache = DeviceListingCache(FakeClock())
	loader = _Loader(["a", "b"])
	first = cache.get_or_list(KEY, loader)
	first.clear()
	# when
	second = cache.get_or_list(KEY, loader)
	# then
	assert [e.name for e in second] == ["a", "b"]


def test_given_more_directories_than_max_when_get_then_least_recently_used_evicted() -> None:
	# given
	cache = DeviceListingCache(FakeClock(), max_directories=2)
	loaders = {p: _Loader() for p in ("a", "b", "c")}
	for p in ("a", "b", "c"):
		cache.get_or_list(("adb", "d", p), loaders[p])
	# when
	cache.get_or_list(("adb", "d", "a"), loaders["a"])
	# then
	assert loaders["a"].calls == 2
	assert loaders["c"].calls == 1


def test_given_recently_used_entry_when_eviction_then_it_survives() -> None:
	# given
	cache = DeviceListingCache(FakeClock(), max_directories=2)
	loaders = {p: _Loader() for p in ("a", "b", "c")}
	cache.get_or_list(("adb", "d", "a"), loaders["a"])
	cache.get_or_list(("adb", "d", "b"), loaders["b"])
	cache.get_or_list(("adb", "d", "a"), loaders["a"])
	# when
	cache.get_or_list(("adb", "d", "c"), loaders["c"])
	cache.get_or_list(("adb", "d", "a"), loaders["a"])
	cache.get_or_list(("adb", "d", "b"), loaders["b"])
	# then
	assert loaders["a"].calls == 1
	assert loaders["b"].calls == 2


def test_given_other_device_or_method_when_get_then_separate_entries() -> None:
	# given
	cache = DeviceListingCache(FakeClock())
	loader = _Loader()
	cache.get_or_list(("adb", "d1", "x"), loader)
	# when
	cache.get_or_list(("adb", "d2", "x"), loader)
	cache.get_or_list(("afc", "d1", "x"), loader)
	# then
	assert loader.calls == 3


def test_given_entries_when_clear_then_reloaded() -> None:
	# given
	cache = DeviceListingCache(FakeClock())
	loader = _Loader()
	cache.get_or_list(KEY, loader)
	# when
	cache.clear()
	cache.get_or_list(KEY, loader)
	# then
	assert loader.calls == 2
