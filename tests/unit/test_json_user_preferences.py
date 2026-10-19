import json

import pytest

from spacemaker.adapters.outbound.preferences.json_store import JsonUserPreferences
from spacemaker.domain.device_browse import DeviceBrowseSort, DeviceBrowseSortKey, SortOrder


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
