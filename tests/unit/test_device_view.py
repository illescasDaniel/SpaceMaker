import pytest

from spacemaker.domain.device_browse import DeviceEntry
from spacemaker.domain.device_view import (
	DEVICE_VIEW_MEMORY_MAX,
	EMPTY_VIEW_MEMORY,
	DeviceFolderCounts,
	DeviceViewHints,
	DeviceViewMode,
	DeviceViewSetting,
	dump_device_view_memory,
	folder_counts,
	folder_view,
	is_media_name,
	parse_device_view_memory,
	remember_view,
	view_hints,
)


GRID = DeviceViewMode.GRID
LIST = DeviceViewMode.LIST


def _memory(*items: tuple[str, DeviceViewMode]) -> dict[str, DeviceViewMode]:
	return dict(items)


# is_media_name


@pytest.mark.parametrize(
	"name",
	[
		"a.jpg",
		"a.JPEG",
		"IMG_1.PNG",
		"x.webp",
		"x.gif",
		"x.heic",
		"x.HEIF",
		"c.mp4",
		"c.MOV",
		"c.m4v",
		"c.3gp",
		"c.mkv",
		"c.webm",
	],
)
def test_given_photo_or_video_name_when_is_media_name_then_true(name: str) -> None:
	# given
	# when
	result = is_media_name(name)
	# then
	assert result


@pytest.mark.parametrize("name", ["notes.txt", "report.pdf", "song.mp3", "photo.dng", "jpg", "archive.jpg.zip", ""])
def test_given_other_name_when_is_media_name_then_false(name: str) -> None:
	# given
	# when
	result = is_media_name(name)
	# then
	assert not result


# folder_counts


def test_given_mixed_entries_when_folder_counts_then_media_files_only_counted_as_media() -> None:
	# given
	entries = [
		DeviceEntry("a.jpg", False),
		DeviceEntry("b.mp4", False),
		DeviceEntry("c.pdf", False),
		DeviceEntry("Sub", True),
	]
	# when
	counts = folder_counts(entries, show_hidden=False)
	# then
	assert counts == DeviceFolderCounts(entry_count=4, media_count=2)


def test_given_folder_named_like_a_photo_when_folder_counts_then_never_media() -> None:
	# given
	entries = [DeviceEntry("album.jpg", True), DeviceEntry("clips.mp4", True)]
	# when
	counts = folder_counts(entries, show_hidden=True)
	# then
	assert counts == DeviceFolderCounts(entry_count=2, media_count=0)


def test_given_hidden_entries_when_show_hidden_off_then_excluded_from_both_counts() -> None:
	# given
	entries = [DeviceEntry(f"p{i}.jpg", False) for i in range(10)]
	entries += [DeviceEntry(f"d{i}.pdf", False) for i in range(10)]
	entries += [DeviceEntry(f".h{i}.jpg", False) for i in range(20)]
	# when
	counts = folder_counts(entries, show_hidden=False)
	# then
	assert counts == DeviceFolderCounts(entry_count=20, media_count=10)


def test_given_hidden_entries_when_show_hidden_on_then_included_in_both_counts() -> None:
	# given
	entries = [DeviceEntry(f"p{i}.jpg", False) for i in range(10)]
	entries += [DeviceEntry(f"d{i}.pdf", False) for i in range(10)]
	entries += [DeviceEntry(f".h{i}.jpg", False) for i in range(20)]
	# when
	counts = folder_counts(entries, show_hidden=True)
	# then
	assert counts == DeviceFolderCounts(entry_count=40, media_count=30)


def test_given_no_entries_when_folder_counts_then_zero() -> None:
	# given
	entries: list[DeviceEntry] = []
	# when
	counts = folder_counts(entries, show_hidden=False)
	# then
	assert counts == DeviceFolderCounts(0, 0)


# folder_view


@pytest.mark.parametrize(
	"name",
	[
		"DCIM",
		"Pictures",
		"Movies",
		"Screenshots",
		"Camera",
		"WhatsApp Images",
		"WhatsApp Video",
		"Telegram Images",
		"Telegram Video",
	],
)
def test_given_grid_table_name_when_folder_view_then_grid(name: str) -> None:
	# given
	# when
	result = folder_view(name)
	# then
	assert result is GRID


@pytest.mark.parametrize("name", ["Documents", "Download", "Android", "Music", "Podcasts", "Recordings"])
def test_given_list_table_name_when_folder_view_then_list(name: str) -> None:
	# given
	# when
	result = folder_view(name)
	# then
	assert result is LIST


@pytest.mark.parametrize(
	("path", "expected"),
	[
		("dcim", GRID),
		("DCIM/camera", GRID),
		("pictures/Instagram", GRID),
		("DOCUMENTS", LIST),
		("whatsapp images", GRID),
	],
)
def test_given_any_case_when_folder_view_then_case_insensitive(path: str, expected: DeviceViewMode) -> None:
	# given
	# when
	result = folder_view(path)
	# then
	assert result is expected


@pytest.mark.parametrize(
	("path", "expected"),
	[
		("DCIM/Camera", GRID),
		("Pictures/Instagram", GRID),
		("Documents/Photos", LIST),
		("Documents/Trip/2024", LIST),
		("Documents/DCIM", GRID),
		("DCIM/x/Documents", LIST),
		("Android/data/com.x/DCIM", GRID),
	],
)
def test_given_nested_path_when_folder_view_then_nearest_ancestor_or_self_wins(
	path: str, expected: DeviceViewMode
) -> None:
	# given
	# when
	result = folder_view(path)
	# then
	assert result is expected


@pytest.mark.parametrize(
	"path", ["", "Backup2024", "Misc/Stuff", "MyDCIM", "DCIM2", "Old Documents", "a/MyPictures/b", "Camera Roll"]
)
def test_given_root_or_no_whole_segment_match_when_folder_view_then_none(path: str) -> None:
	# given
	# when
	result = folder_view(path)
	# then
	assert result is None


# parse_device_view_memory


@pytest.mark.parametrize("raw", [None, "grid", 3, ["DCIM", "grid"], [["DCIM", "grid"]], True])
def test_given_non_object_when_parse_then_empty(raw: object) -> None:
	# given
	# when
	memory = parse_device_view_memory(raw)
	# then
	assert dict(memory) == {}


def test_given_valid_object_when_parse_then_entries_and_order_kept() -> None:
	# given
	raw = {"Z": "list", "DCIM/Camera": "grid", "": "list"}
	# when
	memory = parse_device_view_memory(raw)
	# then
	assert list(memory.items()) == [("Z", LIST), ("DCIM/Camera", GRID), ("", LIST)]


@pytest.mark.parametrize(
	"bad",
	[
		("DCIM/Camera", "table"),
		("DCIM/Camera", "auto"),
		("DCIM/Camera", 1),
		("DCIM/Camera", None),
		("DCIM/Camera", ["grid"]),
		("a/../b", "grid"),
		("../x", "list"),
		("a\x00b", "grid"),
	],
)
def test_given_one_bad_entry_when_parse_then_only_that_entry_dropped(bad: tuple[str, object]) -> None:
	# given
	raw = {"First": "grid", bad[0]: bad[1], "Last": "list"}
	# when
	memory = parse_device_view_memory(raw)
	# then
	assert list(memory.items()) == [("First", GRID), ("Last", LIST)]


def test_given_more_than_cap_when_parse_then_keeps_most_recent() -> None:
	# given
	raw = {f"f{i}": "grid" for i in range(DEVICE_VIEW_MEMORY_MAX + 20)}
	# when
	memory = parse_device_view_memory(raw)
	# then
	keys = list(memory)
	assert len(keys) == DEVICE_VIEW_MEMORY_MAX
	assert keys[0] == "f20"
	assert keys[-1] == f"f{DEVICE_VIEW_MEMORY_MAX + 19}"


def test_given_bad_entries_beyond_cap_when_parse_then_cap_counts_valid_entries_only() -> None:
	# given
	raw: dict[str, object] = {f"f{i}": "grid" for i in range(DEVICE_VIEW_MEMORY_MAX)}
	raw["bad"] = "nope"
	# when
	memory = parse_device_view_memory(raw)
	# then
	assert len(memory) == DEVICE_VIEW_MEMORY_MAX
	assert "f0" in memory


# dump


def test_given_memory_when_dump_then_plain_strings_oldest_first() -> None:
	# given
	memory = _memory(("B", LIST), ("A", GRID))
	# when
	dumped = dump_device_view_memory(memory)
	# then
	assert list(dumped.items()) == [("B", "list"), ("A", "grid")]
	assert all(type(v) is str for v in dumped.values())


def test_given_memory_when_dump_then_parse_round_trips() -> None:
	# given
	memory = _memory(("B", LIST), ("", GRID), ("A/c", LIST))
	# when
	restored = parse_device_view_memory(dump_device_view_memory(memory))
	# then
	assert list(restored.items()) == list(memory.items())


def test_given_empty_memory_when_dump_then_empty_object() -> None:
	# given
	# when
	dumped = dump_device_view_memory(EMPTY_VIEW_MEMORY)
	# then
	assert dumped == {}


# remember_view


def test_given_new_path_when_remember_grid_then_entry_added_as_most_recent() -> None:
	# given
	memory = _memory(("A", LIST))
	# when
	result = remember_view(memory, "B", DeviceViewSetting.GRID)
	# then
	assert list(result.items()) == [("A", LIST), ("B", GRID)]


def test_given_existing_path_when_remember_then_overwritten_and_moved_to_most_recent() -> None:
	# given
	memory = _memory(("A", LIST), ("B", GRID), ("C", LIST))
	# when
	result = remember_view(memory, "A", DeviceViewSetting.GRID)
	# then
	assert list(result.items()) == [("B", GRID), ("C", LIST), ("A", GRID)]


def test_given_same_value_when_remember_again_then_still_moved_to_most_recent() -> None:
	# given
	memory = _memory(("A", LIST), ("B", GRID))
	# when
	result = remember_view(memory, "A", DeviceViewSetting.LIST)
	# then
	assert list(result) == ["B", "A"]


def test_given_existing_path_when_remember_auto_then_deleted() -> None:
	# given
	memory = _memory(("A", LIST), ("B", GRID))
	# when
	result = remember_view(memory, "A", DeviceViewSetting.AUTO)
	# then
	assert list(result.items()) == [("B", GRID)]


def test_given_missing_path_when_remember_auto_then_unchanged_and_no_error() -> None:
	# given
	memory = _memory(("A", LIST))
	# when
	result = remember_view(memory, "Nope", DeviceViewSetting.AUTO)
	# then
	assert list(result.items()) == [("A", LIST)]


def test_given_full_memory_when_remember_501st_then_oldest_dropped_and_size_stays() -> None:
	# given
	memory = {f"f{i}": GRID for i in range(DEVICE_VIEW_MEMORY_MAX)}
	# when
	result = remember_view(memory, "new", DeviceViewSetting.LIST)
	# then
	assert len(result) == DEVICE_VIEW_MEMORY_MAX
	assert "f0" not in result
	assert "f1" in result
	assert list(result)[-1] == "new"


def test_given_full_memory_when_existing_set_again_then_it_is_not_the_next_dropped() -> None:
	# given
	memory = {f"f{i}": GRID for i in range(DEVICE_VIEW_MEMORY_MAX)}
	refreshed = remember_view(memory, "f0", DeviceViewSetting.GRID)
	# when
	result = remember_view(refreshed, "new", DeviceViewSetting.GRID)
	# then
	assert len(result) == DEVICE_VIEW_MEMORY_MAX
	assert "f0" in result
	assert "f1" not in result


def test_given_full_memory_when_existing_overwritten_then_nothing_dropped() -> None:
	# given
	memory = {f"f{i}": GRID for i in range(DEVICE_VIEW_MEMORY_MAX)}
	# when
	result = remember_view(memory, "f7", DeviceViewSetting.LIST)
	# then
	assert len(result) == DEVICE_VIEW_MEMORY_MAX
	assert "f0" in result


def test_given_any_change_when_remember_then_input_memory_unchanged() -> None:
	# given
	memory = _memory(("A", LIST), ("B", GRID))
	snapshot = list(memory.items())
	# when
	remember_view(memory, "A", DeviceViewSetting.GRID)
	remember_view(memory, "C", DeviceViewSetting.LIST)
	remember_view(memory, "B", DeviceViewSetting.AUTO)
	# then
	assert list(memory.items()) == snapshot


# view_hints


def test_given_typed_folder_and_stored_choice_when_view_hints_then_both_reported() -> None:
	# given
	memory = _memory(("DCIM/Camera", LIST))
	# when
	hints = view_hints("DCIM/Camera", memory)
	# then
	assert hints == DeviceViewHints(folder_view=GRID, stored_view=LIST)


def test_given_choice_for_other_folders_when_view_hints_then_stored_is_exact_path_only() -> None:
	# given
	memory = _memory(("DCIM/Camera", LIST))
	# when / then
	assert view_hints("DCIM", memory).stored_view is None
	assert view_hints("DCIM/Camera/Old", memory).stored_view is None
	assert view_hints("DCIM/Screenshots", memory).stored_view is None


def test_given_untyped_folder_and_empty_memory_when_view_hints_then_both_none() -> None:
	# given
	# when
	hints = view_hints("Backup2024", EMPTY_VIEW_MEMORY)
	# then
	assert hints == DeviceViewHints(folder_view=None, stored_view=None)


def test_given_root_with_stored_choice_when_view_hints_then_root_key_matches() -> None:
	# given
	memory = _memory(("", GRID))
	# when
	hints = view_hints("", memory)
	# then
	assert hints == DeviceViewHints(folder_view=None, stored_view=GRID)
