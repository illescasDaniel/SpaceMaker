from pathlib import Path

from spacemaker.bootstrap.paths import normalize_library_root


def test_given_originals_folder_when_normalize_then_parent_library_root(tmp_path: Path) -> None:
	library = tmp_path / "SpaceMakerLibrary"
	originals = library / "originals"
	originals.mkdir(parents=True)
	(originals / "photo.jpg").write_bytes(b"x")

	normalized = normalize_library_root(str(originals))

	assert normalized == str(library.resolve())
	assert (Path(normalized) / "originals" / "photo.jpg").is_file()


def test_given_library_root_when_normalize_then_unchanged(tmp_path: Path) -> None:
	library = tmp_path / "SpaceMakerLibrary"
	library.mkdir()
	assert normalize_library_root(str(library)) == str(library.resolve())
