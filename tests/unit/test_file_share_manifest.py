import zipfile

from spacemaker.application.file_share_manifest import (
	build_share_manifest,
	count_shareable_files_in_root,
	dedupe_share_selection_paths,
	prune_share_selection_paths,
	write_folder_zip,
)


def test_given_file_and_folder_when_build_share_manifest_then_one_row_each(tmp_path):
	file_a = tmp_path / "a.txt"
	file_a.write_text("a", encoding="utf-8")
	sub = tmp_path / "nested"
	sub.mkdir()
	(sub / "b.txt").write_text("b", encoding="utf-8")

	entries = build_share_manifest([str(file_a), str(sub)])

	assert len(entries) == 2
	assert entries[0].kind == "file"
	assert entries[0].display_name == "a.txt"
	assert entries[1].kind == "folder_zip"
	assert entries[1].display_name == "nested"


def test_given_empty_folder_when_count_shareable_files_then_zero(tmp_path):
	empty = tmp_path / "empty"
	empty.mkdir()
	assert count_shareable_files_in_root(empty) == 0


def test_given_nested_empty_subfolder_when_count_shareable_files_then_counts_sibling_files(tmp_path):
	root = tmp_path / "root"
	root.mkdir()
	(root / "empty-sub").mkdir()
	(root / "data.txt").write_text("x", encoding="utf-8")
	assert count_shareable_files_in_root(root) == 1


def test_given_empty_folder_path_when_prune_share_selection_then_dropped(tmp_path):
	empty = tmp_path / "empty"
	empty.mkdir()
	file_a = tmp_path / "a.txt"
	file_a.write_text("a", encoding="utf-8")
	kept, had_empty = prune_share_selection_paths([str(empty), str(file_a)])
	assert had_empty is True
	assert kept == [str(file_a)]


def test_given_duplicate_paths_when_dedupe_share_selection_then_keeps_first(tmp_path):
	file_a = tmp_path / "a.txt"
	file_a.write_text("a", encoding="utf-8")
	path = str(file_a)
	assert dedupe_share_selection_paths([path, path]) == [path]


def test_given_folder_with_files_when_write_folder_zip_then_preserves_relative_paths(tmp_path):
	root = tmp_path / "proj"
	root.mkdir()
	(root / "sub").mkdir()
	(root / "sub" / "inner.txt").write_text("hi", encoding="utf-8")
	zip_path = tmp_path / "out.zip"
	write_folder_zip(root, zip_path)
	with zipfile.ZipFile(zip_path) as archive:
		names = set(archive.namelist())
	assert names == {"sub/inner.txt"}
