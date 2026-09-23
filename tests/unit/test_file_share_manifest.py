from pathlib import Path

from spacemaker.application.file_share_manifest import expand_share_selection


def test_given_file_and_folder_when_expand_share_selection_then_lists_files(tmp_path):
	file_a = tmp_path / "a.txt"
	file_a.write_text("a", encoding="utf-8")
	sub = tmp_path / "nested"
	sub.mkdir()
	(sub / "b.txt").write_text("b", encoding="utf-8")

	pairs = expand_share_selection([str(file_a), str(sub)])

	names = {name for name, _absolute in pairs}
	paths = {Path(path).name for _name, path in pairs}
	assert "a.txt" in names
	assert "b.txt" in names
	assert paths == {"a.txt", "b.txt"}
