from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from tests.unit.fakes import FakeArchiveWriter

from spacemaker.adapters.outbound.filesystem.zip_archive_writer import StoredZipArchiveWriter
from spacemaker.application.download_all import DownloadAll
from spacemaker.domain.download_all import (
	DownloadAllBuildError,
	DownloadAllItem,
	DownloadAllKind,
	NothingToDownloadError,
	dedupe_entry_names,
	sanitize_entry_name,
)
from spacemaker.domain.gallery_batch import ArchiveEntry


def _file(path: Path, data: bytes = b"x") -> str:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_bytes(data)
	return str(path)


def _names(writer: FakeArchiveWriter) -> list[str]:
	return [entry.entry_name for entry in writer.written[-1][1]]


# --- domain ---


@pytest.mark.parametrize(
	("kind", "expected"),
	[(DownloadAllKind.SHARE, "SpaceMaker-share.zip"), (DownloadAllKind.TRANSFER, "SpaceMaker-transfer.zip")],
)
def test_given_kind_when_zip_filename_then_spacemaker_prefixed_name(kind, expected) -> None:
	# given
	# when
	name = kind.zip_filename
	# then
	assert name == expected


@pytest.mark.parametrize(
	"raw",
	["../x", "a/../../x", "/etc/passwd", "C:\\x", "C:/x", "..\\..\\x", "a\\..\\..\\b", "//server/share/x"],
)
def test_given_hostile_name_when_sanitize_then_plain_relative_name_inside_archive(raw: str) -> None:
	# given
	# when
	safe = sanitize_entry_name(raw)
	# then
	assert safe
	assert ".." not in safe.split("/")
	assert not safe.startswith("/")
	assert "\\" not in safe
	assert ":" not in safe.split("/")[0]


def test_given_parent_traversal_when_sanitize_then_only_the_leaf_survives() -> None:
	# given
	# when
	safe = sanitize_entry_name("../x")
	# then
	assert safe == "x"


def test_given_backslash_relative_path_when_sanitize_then_forward_slashes() -> None:
	# given
	# when
	safe = sanitize_entry_name("vacation\\day1\\a.jpg")
	# then
	assert safe == "vacation/day1/a.jpg"


def test_given_drive_letter_path_when_sanitize_then_drive_dropped() -> None:
	# given
	# when
	safe = sanitize_entry_name("C:\\x")
	# then
	assert safe == "x"


@pytest.mark.parametrize("raw", ["", "   ", "/", "..", "../.."])
def test_given_empty_or_unusable_name_when_sanitize_then_non_empty_fallback(raw: str) -> None:
	# given
	# when
	safe = sanitize_entry_name(raw)
	# then
	assert safe.strip()
	assert ".." not in safe.split("/")


def test_given_plain_name_when_sanitize_then_unchanged() -> None:
	# given
	# when
	safe = sanitize_entry_name("report.pdf")
	# then
	assert safe == "report.pdf"


def test_given_duplicate_names_when_dedupe_then_second_gets_suffix_and_order_kept() -> None:
	# given
	names = ["report.pdf", "a.txt", "report.pdf", "report.pdf"]
	# when
	result = dedupe_entry_names(names)
	# then
	assert result == ["report.pdf", "a.txt", "report (2).pdf", "report (3).pdf"]


def test_given_unique_names_when_dedupe_then_unchanged() -> None:
	# given
	names = ["a.txt", "b.txt"]
	# when
	result = dedupe_entry_names(names)
	# then
	assert result == names


# --- use case ---


def test_given_file_and_folder_rows_when_build_then_file_by_name_and_folder_with_relative_paths(tmp_path) -> None:
	# given
	report = _file(tmp_path / "src" / "report.pdf")
	vacation = tmp_path / "src" / "vacation"
	_file(vacation / "a.jpg")
	_file(vacation / "day2" / "b.jpg")
	writer = FakeArchiveWriter()
	items = [
		DownloadAllItem("report.pdf", report, is_folder=False),
		DownloadAllItem("vacation", str(vacation), is_folder=True),
	]
	destination = str(tmp_path / "out.zip")
	# when
	DownloadAll(writer).build(DownloadAllKind.SHARE, items, destination)
	# then
	assert writer.written[-1][0] == destination
	assert sorted(_names(writer)) == ["report.pdf", "vacation/a.jpg", "vacation/day2/b.jpg"]
	sources = {entry.entry_name: entry.source_path for entry in writer.written[-1][1]}
	assert sources["vacation/day2/b.jpg"] == str(vacation / "day2" / "b.jpg")


def test_given_two_items_with_same_name_when_build_then_second_is_suffixed_and_sources_untouched(tmp_path) -> None:
	# given
	first = _file(tmp_path / "t1" / "report.pdf", b"one")
	second = _file(tmp_path / "t2" / "report.pdf", b"two")
	writer = FakeArchiveWriter()
	items = [DownloadAllItem("report.pdf", first, False), DownloadAllItem("report.pdf", second, False)]
	# when
	DownloadAll(writer).build(DownloadAllKind.TRANSFER, items, str(tmp_path / "out.zip"))
	# then
	assert _names(writer) == ["report.pdf", "report (2).pdf"]
	assert Path(first).read_bytes() == b"one"
	assert Path(second).read_bytes() == b"two"


def test_given_hostile_item_name_when_build_then_entry_name_is_sanitized(tmp_path) -> None:
	# given
	source = _file(tmp_path / "src" / "evil.bin")
	writer = FakeArchiveWriter()
	items = [DownloadAllItem("../../etc/evil.bin", source, False)]
	# when
	DownloadAll(writer).build(DownloadAllKind.TRANSFER, items, str(tmp_path / "out.zip"))
	# then
	assert _names(writer) == ["evil.bin"]


def test_given_no_items_when_build_then_nothing_to_download_and_no_archive(tmp_path) -> None:
	# given
	writer = FakeArchiveWriter()
	destination = tmp_path / "out.zip"
	# when
	# then
	with pytest.raises(NothingToDownloadError):
		DownloadAll(writer).build(DownloadAllKind.SHARE, [], str(destination))
	assert not destination.exists()


def test_given_only_vanished_files_when_build_then_nothing_to_download(tmp_path) -> None:
	# given
	writer = FakeArchiveWriter()
	items = [DownloadAllItem("gone.txt", str(tmp_path / "gone.txt"), False)]
	# when
	# then
	with pytest.raises(NothingToDownloadError):
		DownloadAll(writer).build(DownloadAllKind.SHARE, items, str(tmp_path / "out.zip"))


def test_given_empty_folder_only_when_build_then_nothing_to_download(tmp_path) -> None:
	# given
	empty = tmp_path / "empty"
	empty.mkdir()
	writer = FakeArchiveWriter()
	items = [DownloadAllItem("empty", str(empty), True)]
	# when
	# then
	with pytest.raises(NothingToDownloadError):
		DownloadAll(writer).build(DownloadAllKind.SHARE, items, str(tmp_path / "out.zip"))


def test_given_one_vanished_file_of_three_when_build_then_other_two_archived(tmp_path) -> None:
	# given
	one = _file(tmp_path / "one.txt")
	three = _file(tmp_path / "three.txt")
	writer = FakeArchiveWriter()
	items = [
		DownloadAllItem("one.txt", one, False),
		DownloadAllItem("two.txt", str(tmp_path / "two.txt"), False),
		DownloadAllItem("three.txt", three, False),
	]
	# when
	DownloadAll(writer).build(DownloadAllKind.SHARE, items, str(tmp_path / "out.zip"))
	# then
	assert _names(writer) == ["one.txt", "three.txt"]


def test_given_writer_raises_oserror_when_build_then_download_all_build_error(tmp_path) -> None:
	# given
	source = _file(tmp_path / "a.txt")
	writer = FakeArchiveWriter(error=OSError(28, "No space left on device"))
	# when
	# then
	with pytest.raises(DownloadAllBuildError):
		DownloadAll(writer).build(
			DownloadAllKind.SHARE, [DownloadAllItem("a.txt", source, False)], str(tmp_path / "o.zip")
		)


# --- adapter: StoredZipArchiveWriter skip_missing ---


def test_given_missing_source_and_skip_missing_when_write_zip_then_skipped_and_count_returned(tmp_path) -> None:
	# given
	present = _file(tmp_path / "a.bin", b"a")
	destination = tmp_path / "out" / "x.zip"
	entries = [ArchiveEntry(present, "a.bin"), ArchiveEntry(str(tmp_path / "gone.bin"), "gone.bin")]
	# when
	written = StoredZipArchiveWriter().write_stored_zip(str(destination), entries, skip_missing=True)
	# then
	assert written == 1
	with zipfile.ZipFile(destination) as archive:
		assert archive.namelist() == ["a.bin"]


def test_given_present_sources_when_write_zip_then_count_is_number_of_entries(tmp_path) -> None:
	# given
	entries = [ArchiveEntry(_file(tmp_path / "a.bin"), "a.bin"), ArchiveEntry(_file(tmp_path / "b.bin"), "b.bin")]
	# when
	written = StoredZipArchiveWriter().write_stored_zip(str(tmp_path / "x.zip"), entries)
	# then
	assert written == 2


def test_given_missing_source_and_default_when_write_zip_then_still_raises_and_leaves_nothing(tmp_path) -> None:
	# given
	destination = tmp_path / "out" / "x.zip"
	entries = [ArchiveEntry(str(tmp_path / "gone.bin"), "gone.bin")]
	# when
	# then
	with pytest.raises(FileNotFoundError):
		StoredZipArchiveWriter().write_stored_zip(str(destination), entries)
	assert list((tmp_path / "out").iterdir()) == []


def test_given_only_missing_sources_and_skip_missing_when_write_zip_then_zero_returned(tmp_path) -> None:
	# given
	entries = [ArchiveEntry(str(tmp_path / "gone.bin"), "gone.bin")]
	# when
	written = StoredZipArchiveWriter().write_stored_zip(str(tmp_path / "x.zip"), entries, skip_missing=True)
	# then
	assert written == 0


def test_given_write_failure_with_skip_missing_when_write_zip_then_no_partial_file_left(tmp_path, monkeypatch) -> None:
	# given
	present = _file(tmp_path / "a.bin")
	destination = tmp_path / "out" / "x.zip"

	def boom(*_args, **_kwargs) -> None:
		raise OSError(28, "No space left on device")

	monkeypatch.setattr(zipfile.ZipFile, "write", boom)
	# when
	# then
	with pytest.raises(OSError):
		StoredZipArchiveWriter().write_stored_zip(str(destination), [ArchiveEntry(present, "a.bin")], skip_missing=True)
	assert list((tmp_path / "out").iterdir()) == []
