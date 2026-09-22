from pathlib import Path

from spacemaker.adapters.outbound.filesystem.local import LocalFileSystem
from spacemaker.domain.library import LibraryFolder


def test_given_thumbnails_folder_when_list_originals_then_skipped(tmp_path: Path) -> None:
	library = tmp_path / "lib"
	thumbs = library / "originals" / "DCIM" / ".thumbnails"
	thumbs.mkdir(parents=True)
	(thumbs / "tiny.jpg").write_bytes(b"x")
	(library / "originals" / "photo.jpg").write_bytes(b"y")

	fs = LocalFileSystem()
	root = str(library)
	listed = fs.list_files_in_library_folder(root, LibraryFolder.ORIGINALS)

	assert listed == ["photo.jpg"]
	assert fs.count_files_in_folder(root, LibraryFolder.ORIGINALS) == 1


def test_given_nested_files_when_list_and_count_then_match(tmp_path: Path) -> None:
	library = tmp_path / "lib"
	originals = library / "originals" / "2024"
	originals.mkdir(parents=True)
	(originals / "a.jpg").write_bytes(b"x")
	(originals / "b.jpg").write_bytes(b"y")

	fs = LocalFileSystem()
	root = str(library)
	listed = fs.list_files_in_library_folder(root, LibraryFolder.ORIGINALS)
	counted = fs.count_files_in_folder(root, LibraryFolder.ORIGINALS)

	assert counted == 2
	assert listed == ["2024/a.jpg", "2024/b.jpg"]
