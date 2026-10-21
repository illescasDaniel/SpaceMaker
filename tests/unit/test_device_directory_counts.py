from tests.unit.fakes import FakeDeviceRepository
from tests.unit.passcode_fakes import FakeClock

from spacemaker.application.device_listing_cache import DeviceListingCache
from spacemaker.application.list_device_directory import ListDeviceDirectory
from spacemaker.domain.device_browse import DeviceBrowseQuery, DeviceEntry, scroll_page


def _photos_and_pdfs(devices: FakeDeviceRepository, path: str = "Misc") -> None:
	devices.tree[path] = (
		[DeviceEntry(f"p{i}.jpg", False) for i in range(10)]
		+ [DeviceEntry(f"d{i}.pdf", False) for i in range(10)]
		+ [DeviceEntry(f".h{i}.jpg", False) for i in range(20)]
	)


def _use_case(devices: FakeDeviceRepository) -> ListDeviceDirectory:
	return ListDeviceDirectory(devices, cache=DeviceListingCache(FakeClock()))


def test_given_hidden_media_when_scroll_then_counts_exclude_hidden_entries() -> None:
	# given
	devices = FakeDeviceRepository()
	_photos_and_pdfs(devices)
	# when
	page = _use_case(devices).scroll("adb", "dev1", "Misc", DeviceBrowseQuery())
	# then
	assert (page.entry_count, page.media_count) == (20, 10)


def test_given_show_hidden_when_scroll_then_counts_include_hidden_entries() -> None:
	# given
	devices = FakeDeviceRepository()
	_photos_and_pdfs(devices)
	# when
	page = _use_case(devices).scroll("adb", "dev1", "Misc", DeviceBrowseQuery(show_hidden=True))
	# then
	assert (page.entry_count, page.media_count) == (40, 30)


def test_given_query_when_scroll_then_counts_ignore_it_but_total_follows_it() -> None:
	# given
	devices = FakeDeviceRepository()
	_photos_and_pdfs(devices)
	use_case = _use_case(devices)
	# when
	unfiltered = use_case.scroll("adb", "dev1", "Misc", DeviceBrowseQuery(show_hidden=True))
	filtered = use_case.scroll("adb", "dev1", "Misc", DeviceBrowseQuery(show_hidden=True, query=".pdf"))
	# then
	assert (filtered.entry_count, filtered.media_count) == (unfiltered.entry_count, unfiltered.media_count) == (40, 30)
	assert filtered.total == 10
	assert [e.name for e in filtered.entries][0].endswith(".pdf")


def test_given_query_matching_nothing_when_scroll_then_counts_still_describe_the_folder() -> None:
	# given
	entries = [DeviceEntry(f"p{i}.jpg", False) for i in range(5)]
	# when
	page = scroll_page("DCIM", entries, DeviceBrowseQuery(query="zzz"))
	# then
	assert page.total == 0
	assert (page.entry_count, page.media_count) == (5, 5)


def test_given_folders_only_when_scroll_then_media_count_zero() -> None:
	# given
	entries = [DeviceEntry("A", True), DeviceEntry("B.jpg", True)]
	# when
	page = scroll_page("", entries, DeviceBrowseQuery())
	# then
	assert (page.entry_count, page.media_count) == (2, 0)


def test_given_cursor_page_when_scroll_then_counts_still_cover_whole_folder() -> None:
	# given
	entries = [DeviceEntry(f"f{i:03d}.jpg", False) for i in range(250)]
	first = scroll_page("DCIM", entries, DeviceBrowseQuery(limit=100))
	# when
	second = scroll_page("DCIM", entries, DeviceBrowseQuery(limit=100, cursor=first.next_cursor))
	# then
	assert (second.entry_count, second.media_count) == (250, 250)


def test_given_cache_when_scroll_with_counts_then_exactly_one_device_call() -> None:
	# given
	devices = FakeDeviceRepository()
	_photos_and_pdfs(devices)
	use_case = _use_case(devices)
	# when
	use_case.scroll("adb", "dev1", "Misc", DeviceBrowseQuery())
	use_case.scroll("adb", "dev1", "Misc", DeviceBrowseQuery(show_hidden=True))
	use_case.scroll("adb", "dev1", "Misc", DeviceBrowseQuery(query="p1"))
	# then
	assert devices.list_directory_calls == ["Misc"]
