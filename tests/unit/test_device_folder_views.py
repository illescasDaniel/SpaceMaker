import pytest
from tests.unit.fakes import FakeUserPreferences

from spacemaker.application.device_folder_views import DeviceFolderViews
from spacemaker.domain.device_browse import DeviceBrowseError, DeviceBrowseErrorKind
from spacemaker.domain.device_view import DeviceViewHints, DeviceViewMode, DeviceViewSetting


def test_given_stored_choice_when_hints_then_folder_type_and_stored_view() -> None:
	# given
	prefs = FakeUserPreferences()
	prefs.set_device_picker_view("DCIM/Camera", DeviceViewSetting.LIST)
	use_case = DeviceFolderViews(prefs)
	# when
	hints = use_case.hints("DCIM/Camera")
	# then
	assert hints == DeviceViewHints(folder_view=DeviceViewMode.GRID, stored_view=DeviceViewMode.LIST)


def test_given_prefixed_path_when_hints_then_normalized_before_lookup() -> None:
	# given
	prefs = FakeUserPreferences()
	prefs.set_device_picker_view("Documents", DeviceViewSetting.GRID)
	use_case = DeviceFolderViews(prefs)
	# when
	hints = use_case.hints("/sdcard/Documents/")
	# then
	assert hints == DeviceViewHints(folder_view=DeviceViewMode.LIST, stored_view=DeviceViewMode.GRID)


def test_given_no_preferences_when_hints_then_stored_view_none() -> None:
	# given
	use_case = DeviceFolderViews()
	# when
	hints = use_case.hints("Pictures/x")
	# then
	assert hints == DeviceViewHints(folder_view=DeviceViewMode.GRID, stored_view=None)


def test_given_hints_when_called_then_preferences_not_written() -> None:
	# given
	prefs = FakeUserPreferences()
	# when
	DeviceFolderViews(prefs).hints("DCIM")
	# then
	assert prefs.picker_view_writes == []


@pytest.mark.parametrize("path", ["../data", "a/../../b", "a\x00b"])
def test_given_invalid_path_when_hints_then_invalid_path_error(path: str) -> None:
	# given
	use_case = DeviceFolderViews(FakeUserPreferences())
	# when / then
	with pytest.raises(DeviceBrowseError) as exc:
		use_case.hints(path)
	assert exc.value.kind is DeviceBrowseErrorKind.INVALID_PATH


@pytest.mark.parametrize("setting", [DeviceViewSetting.LIST, DeviceViewSetting.GRID])
def test_given_list_or_grid_when_choose_then_stored_through_port(setting: DeviceViewSetting) -> None:
	# given
	prefs = FakeUserPreferences()
	# when
	DeviceFolderViews(prefs).choose("DCIM/Camera", setting)
	# then
	assert prefs.picker_view_writes == [("DCIM/Camera", setting)]
	assert dict(prefs.get_device_picker_views()) == {"DCIM/Camera": DeviceViewMode(setting.value)}


def test_given_prefixed_path_when_choose_then_normalized_key_stored() -> None:
	# given
	prefs = FakeUserPreferences()
	# when
	DeviceFolderViews(prefs).choose("/sdcard/DCIM/Camera/", DeviceViewSetting.LIST)
	# then
	assert prefs.picker_view_writes == [("DCIM/Camera", DeviceViewSetting.LIST)]


def test_given_stored_choice_when_choose_auto_then_removed() -> None:
	# given
	prefs = FakeUserPreferences()
	prefs.set_device_picker_view("DCIM/Camera", DeviceViewSetting.LIST)
	# when
	DeviceFolderViews(prefs).choose("DCIM/Camera", DeviceViewSetting.AUTO)
	# then
	assert dict(prefs.get_device_picker_views()) == {}


def test_given_nothing_stored_when_choose_auto_then_no_error() -> None:
	# given
	prefs = FakeUserPreferences()
	# when
	DeviceFolderViews(prefs).choose("Nope", DeviceViewSetting.AUTO)
	# then
	assert dict(prefs.get_device_picker_views()) == {}


@pytest.mark.parametrize("path", ["../data", "a/../../b", "a\x00b"])
def test_given_invalid_path_when_choose_then_error_before_any_write(path: str) -> None:
	# given
	prefs = FakeUserPreferences()
	# when / then
	with pytest.raises(DeviceBrowseError) as exc:
		DeviceFolderViews(prefs).choose(path, DeviceViewSetting.GRID)
	assert exc.value.kind is DeviceBrowseErrorKind.INVALID_PATH
	assert prefs.picker_view_writes == []


def test_given_no_preferences_when_choose_then_no_op() -> None:
	# given
	use_case = DeviceFolderViews()
	# when
	use_case.choose("DCIM", DeviceViewSetting.LIST)
	# then
	assert use_case.hints("DCIM").stored_view is None
