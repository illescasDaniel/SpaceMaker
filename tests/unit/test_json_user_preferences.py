import json

import pytest

from spacemaker.adapters.outbound.preferences.json_store import JsonUserPreferences
from spacemaker.domain.device_browse import DeviceBrowseSort, DeviceBrowseSortKey, SortOrder
from spacemaker.domain.device_view import DEVICE_VIEW_MEMORY_MAX, DeviceViewMode, DeviceViewSetting


def test_given_missing_file_when_get_compress_media_then_none(tmp_path):
	# given
	prefs = JsonUserPreferences(tmp_path / "preferences.json")

	# when / then
	assert prefs.get_compress_media() is None


def test_given_set_false_when_get_compress_media_then_false(tmp_path):
	# given
	path = tmp_path / "preferences.json"
	prefs = JsonUserPreferences(path)

	# when
	prefs.set_compress_media(False)

	# then
	assert prefs.get_compress_media() is False
	assert path.is_file()


def test_given_set_true_when_reloaded_then_persists(tmp_path):
	# given
	path = tmp_path / "preferences.json"
	JsonUserPreferences(path).set_compress_media(True)

	# when
	reloaded = JsonUserPreferences(path)

	# then
	assert reloaded.get_compress_media() is True


def test_given_corrupt_json_when_get_compress_media_then_none(tmp_path):
	# given
	path = tmp_path / "preferences.json"
	path.write_text("{not-json", encoding="utf-8")
	prefs = JsonUserPreferences(path)

	# when / then
	assert prefs.get_compress_media() is None


def test_given_other_keys_when_set_compress_media_then_preserves_them(tmp_path):
	# given
	path = tmp_path / "preferences.json"
	path.write_text('{"other": 1}\n', encoding="utf-8")
	prefs = JsonUserPreferences(path)

	# when
	prefs.set_compress_media(False)

	# then
	assert prefs.get_compress_media() is False
	raw = path.read_text(encoding="utf-8")
	assert '"other"' in raw


def test_given_destination_set_when_reloaded_then_persists_and_none_restores_default(tmp_path):
	# given
	path = tmp_path / "preferences.json"
	JsonUserPreferences(path).set_usb_transfer_destination("/data/phone")

	# when
	reloaded = JsonUserPreferences(path)

	# then
	assert reloaded.get_usb_transfer_destination() == "/data/phone"
	reloaded.set_usb_transfer_destination(None)
	assert reloaded.get_usb_transfer_destination() is None


def test_given_destination_and_compress_when_clear_then_both_gone(tmp_path):
	# given
	prefs = JsonUserPreferences(tmp_path / "preferences.json")
	prefs.set_usb_transfer_destination("/data/phone")
	prefs.set_compress_media(False)

	# when
	prefs.clear()

	# then
	assert prefs.get_usb_transfer_destination() is None
	assert prefs.get_compress_media() is None


def test_given_picker_sort_set_when_reloaded_then_same_sort_and_json_shape(tmp_path):
	# given
	path = tmp_path / "preferences.json"
	sort = DeviceBrowseSort(DeviceBrowseSortKey.SIZE, SortOrder.DESC)

	# when
	JsonUserPreferences(path).set_device_picker_sort(sort)

	# then
	assert JsonUserPreferences(path).get_device_picker_sort() == sort
	assert json.loads(path.read_text(encoding="utf-8")) == {"device_picker_sort": {"sort": "size", "order": "desc"}}


def test_given_picker_sort_and_destination_when_set_none_then_only_sort_removed(tmp_path):
	# given
	path = tmp_path / "preferences.json"
	prefs = JsonUserPreferences(path)
	prefs.set_usb_transfer_destination("/data/phone")
	prefs.set_device_picker_sort(DeviceBrowseSort(DeviceBrowseSortKey.MTIME, SortOrder.DESC))

	# when
	prefs.set_device_picker_sort(None)

	# then
	assert prefs.get_device_picker_sort() is None
	raw = json.loads(path.read_text(encoding="utf-8"))
	assert "device_picker_sort" not in raw
	assert prefs.get_usb_transfer_destination() == "/data/phone"


@pytest.mark.parametrize(
	"stored",
	[
		"size-desc",
		{"sort": "type", "order": "asc"},
		{"sort": "size"},
		["size", "desc"],
	],
)
def test_given_corrupt_stored_sort_when_get_then_none(tmp_path, stored):
	# given
	path = tmp_path / "preferences.json"
	path.write_text(json.dumps({"device_picker_sort": stored}), encoding="utf-8")

	# when / then
	assert JsonUserPreferences(path).get_device_picker_sort() is None


def test_given_picker_sort_when_clear_then_none(tmp_path):
	# given
	prefs = JsonUserPreferences(tmp_path / "preferences.json")
	prefs.set_device_picker_sort(DeviceBrowseSort(DeviceBrowseSortKey.SIZE, SortOrder.ASC))

	# when
	prefs.clear()

	# then
	assert prefs.get_device_picker_sort() is None


def test_given_views_set_when_reloaded_then_same_map_and_order_and_json_shape(tmp_path):
	# given
	path = tmp_path / "preferences.json"
	prefs = JsonUserPreferences(path)

	# when
	prefs.set_device_picker_view("DCIM/Camera", DeviceViewSetting.LIST)
	prefs.set_device_picker_view("Documents", DeviceViewSetting.GRID)

	# then
	reloaded = JsonUserPreferences(path).get_device_picker_views()
	assert list(reloaded.items()) == [("DCIM/Camera", DeviceViewMode.LIST), ("Documents", DeviceViewMode.GRID)]
	assert json.loads(path.read_text(encoding="utf-8")) == {
		"device_picker_views": {"DCIM/Camera": "list", "Documents": "grid"}
	}


def test_given_missing_file_when_get_views_then_empty(tmp_path):
	# given
	prefs = JsonUserPreferences(tmp_path / "preferences.json")

	# when / then
	assert dict(prefs.get_device_picker_views()) == {}


@pytest.mark.parametrize("stored", ["grid", ["DCIM", "grid"], 7, None])
def test_given_corrupt_stored_views_when_get_then_empty(tmp_path, stored):
	# given
	path = tmp_path / "preferences.json"
	path.write_text(json.dumps({"device_picker_views": stored}), encoding="utf-8")

	# when / then
	assert dict(JsonUserPreferences(path).get_device_picker_views()) == {}


def test_given_bad_entries_when_get_views_then_only_valid_ones_survive(tmp_path):
	# given
	path = tmp_path / "preferences.json"
	stored = {"DCIM/Camera": "table", "a/../b": "grid", "Documents": "grid", "Music": "list"}
	path.write_text(json.dumps({"device_picker_views": stored}), encoding="utf-8")

	# when
	views = JsonUserPreferences(path).get_device_picker_views()

	# then
	assert list(views.items()) == [("Documents", DeviceViewMode.GRID), ("Music", DeviceViewMode.LIST)]


def test_given_corrupt_file_when_set_view_then_overwritten_with_valid_map(tmp_path):
	# given
	path = tmp_path / "preferences.json"
	path.write_text("{not-json", encoding="utf-8")
	prefs = JsonUserPreferences(path)

	# when
	prefs.set_device_picker_view("DCIM", DeviceViewSetting.LIST)

	# then
	assert dict(prefs.get_device_picker_views()) == {"DCIM": DeviceViewMode.LIST}


def test_given_other_keys_when_set_view_then_preserved(tmp_path):
	# given
	path = tmp_path / "preferences.json"
	prefs = JsonUserPreferences(path)
	prefs.set_usb_transfer_destination("/data/phone")
	prefs.set_device_picker_sort(DeviceBrowseSort(DeviceBrowseSortKey.SIZE, SortOrder.DESC))

	# when
	prefs.set_device_picker_view("DCIM", DeviceViewSetting.GRID)

	# then
	assert prefs.get_usb_transfer_destination() == "/data/phone"
	assert prefs.get_device_picker_sort() == DeviceBrowseSort(DeviceBrowseSortKey.SIZE, SortOrder.DESC)


def test_given_stored_view_when_set_auto_then_entry_removed_and_missing_is_fine(tmp_path):
	# given
	prefs = JsonUserPreferences(tmp_path / "preferences.json")
	prefs.set_device_picker_view("DCIM", DeviceViewSetting.LIST)
	prefs.set_device_picker_view("Music", DeviceViewSetting.GRID)

	# when
	prefs.set_device_picker_view("DCIM", DeviceViewSetting.AUTO)
	prefs.set_device_picker_view("Never/Stored", DeviceViewSetting.AUTO)

	# then
	assert dict(prefs.get_device_picker_views()) == {"Music": DeviceViewMode.GRID}


def test_given_full_map_when_set_501st_then_oldest_dropped_across_restart(tmp_path):
	# given
	path = tmp_path / "preferences.json"
	prefs = JsonUserPreferences(path)
	for i in range(DEVICE_VIEW_MEMORY_MAX):
		prefs.set_device_picker_view(f"f{i}", DeviceViewSetting.GRID)

	# when
	prefs.set_device_picker_view("f0", DeviceViewSetting.LIST)
	prefs.set_device_picker_view("new", DeviceViewSetting.LIST)

	# then
	views = JsonUserPreferences(path).get_device_picker_views()
	assert len(views) == DEVICE_VIEW_MEMORY_MAX
	assert "f0" in views
	assert "f1" not in views
	assert list(views)[-1] == "new"


def test_given_views_when_get_then_reading_does_not_reorder_or_write(tmp_path):
	# given
	path = tmp_path / "preferences.json"
	prefs = JsonUserPreferences(path)
	prefs.set_device_picker_view("A", DeviceViewSetting.GRID)
	prefs.set_device_picker_view("B", DeviceViewSetting.GRID)
	before = path.read_text(encoding="utf-8")

	# when
	prefs.get_device_picker_views()

	# then
	assert path.read_text(encoding="utf-8") == before


def test_given_views_and_compress_when_clear_then_views_empty(tmp_path):
	# given
	prefs = JsonUserPreferences(tmp_path / "preferences.json")
	prefs.set_device_picker_view("DCIM/Camera", DeviceViewSetting.LIST)
	prefs.set_compress_media(False)

	# when
	prefs.clear()

	# then
	assert dict(prefs.get_device_picker_views()) == {}
	assert prefs.get_compress_media() is None


def test_given_concurrent_sets_when_all_done_then_every_view_kept(tmp_path):
	# given
	import threading

	prefs = JsonUserPreferences(tmp_path / "preferences.json")
	threads = [
		threading.Thread(target=prefs.set_device_picker_view, args=(f"f{i}", DeviceViewSetting.GRID)) for i in range(20)
	]

	# when
	for t in threads:
		t.start()
	for t in threads:
		t.join()

	# then
	assert {f"f{i}" for i in range(20)} == set(prefs.get_device_picker_views())
