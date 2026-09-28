from pathlib import Path

from spacemaker.adapters.outbound.filesystem.local import LocalFileSystem
from spacemaker.domain.library import LibraryFolder


def test_given_legacy_converted_only_when_ensure_then_renames_to_processed(tmp_path: Path):
	# given
	library = tmp_path / "lib"
	legacy = library / "converted"
	legacy.mkdir(parents=True)
	(legacy / "photo.avif").write_bytes(b"x")
	fs = LocalFileSystem()
	# when
	fs.ensure_library_folders(str(library))
	# then
	assert not legacy.exists()
	processed = library / LibraryFolder.PROCESSED.value
	assert processed.is_dir()
	assert (processed / "photo.avif").read_bytes() == b"x"


def test_given_both_legacy_and_processed_when_ensure_then_merges(tmp_path: Path):
	# given
	library = tmp_path / "lib"
	legacy = library / "converted"
	processed = library / "processed"
	legacy.mkdir(parents=True)
	processed.mkdir(parents=True)
	(legacy / "old.avif").write_bytes(b"old")
	(processed / "new.avif").write_bytes(b"new")
	fs = LocalFileSystem()
	# when
	fs.ensure_library_folders(str(library))
	# then
	assert not legacy.exists()
	assert (processed / "old.avif").read_bytes() == b"old"
	assert (processed / "new.avif").read_bytes() == b"new"
