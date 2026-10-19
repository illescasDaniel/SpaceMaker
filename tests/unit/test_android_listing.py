import pytest

from spacemaker.adapters.outbound.device.android_listing import (
	android_list_command,
	classify_android_shell_failure,
	parse_android_stat_listing,
)
from spacemaker.domain.device_browse import DeviceBrowseErrorKind, DeviceEntry


def test_given_stat_lines_when_parse_then_entries_with_size_and_mtime() -> None:
	# given
	output = "directory|4096|1760000000|./Camera\nregular file|2048|1760000100|./notes.txt\n"
	# when
	entries = parse_android_stat_listing(output)
	# then
	assert entries == [
		DeviceEntry("Camera", True, 4096, 1760000000),
		DeviceEntry("notes.txt", False, 2048, 1760000100),
	]


def test_given_awkward_names_when_parse_then_exact_names_kept() -> None:
	# given
	output = (
		"regular file|1|1|./résumé final (2).pdf\n"
		"regular file|2|1|./a'b.txt\n"
		"regular file|3|1|./$HOME.txt\n"
		"regular file|4|1|./pipe|name.txt\n"
		"symbolic link|0|1|./link\n"
	)
	# when
	names = [e.name for e in parse_android_stat_listing(output)]
	# then
	assert names == ["résumé final (2).pdf", "a'b.txt", "$HOME.txt", "pipe|name.txt", "link"]


def test_given_newline_in_name_when_parse_then_one_entry_with_exact_name() -> None:
	# given
	output = "regular file|1|1|./a\nb.txt\nregular file|2|2|./c.txt\n"
	# when
	entries = parse_android_stat_listing(output)
	# then
	assert [e.name for e in entries] == ["a\nb.txt", "c.txt"]


def test_given_error_and_blank_lines_when_parse_then_ignored() -> None:
	# given
	output = "\nstat: './broken': No such file or directory\nregular file|5|9|./ok.jpg\n"
	# when
	entries = parse_android_stat_listing(output)
	# then
	assert entries == [DeviceEntry("ok.jpg", False, 5, 9)]


def test_given_root_when_command_then_sdcard_cd_and_not_recursive() -> None:
	# given
	# when
	command = android_list_command("")
	# then
	assert command.startswith("cd /sdcard && ")
	assert "-maxdepth 1" in command


def test_given_hostile_path_when_command_then_path_is_one_quoted_argument() -> None:
	# given
	path = "a b/$(reboot)/it's"
	# when
	command = android_list_command(path)
	# then
	assert "cd '/sdcard/a b/$(reboot)/it'\"'\"'s' && " in command


@pytest.mark.parametrize(
	("text", "kind"),
	[
		("cd: /sdcard/Android/data: Permission denied", DeviceBrowseErrorKind.PERMISSION_DENIED),
		("find: ./x: Permission denied", DeviceBrowseErrorKind.PERMISSION_DENIED),
		("sh: cd: /sdcard/nope: No such file or directory", DeviceBrowseErrorKind.NOT_FOUND),
		("error: device unauthorized.", DeviceBrowseErrorKind.UNAUTHORIZED),
		("error: device 'X' not found", DeviceBrowseErrorKind.UNPLUGGED),
		("error: device offline", DeviceBrowseErrorKind.UNPLUGGED),
		("something odd", DeviceBrowseErrorKind.FAILED),
	],
)
def test_given_shell_failure_text_when_classify_then_kind(text: str, kind: DeviceBrowseErrorKind) -> None:
	# given
	# when
	result = classify_android_shell_failure(text)
	# then
	assert result is kind
