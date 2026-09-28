from datetime import datetime
from pathlib import Path

import pytest

from spacemaker.adapters.outbound.filesystem.local import LocalFileSystem
from spacemaker.adapters.outbound.gallery.sqlite_index import SqliteGalleryIndex
from spacemaker.adapters.outbound.preferences.json_store import JsonUserPreferences
from spacemaker.application.clear_user_preferences import ClearUserPreferences
from spacemaker.application.reset_library import ResetLibrary
from spacemaker.domain.gallery_index import GalleryIndexRow
from spacemaker.domain.library import LibraryFolder, gallery_index_path
from spacemaker.domain.media import MediaKind


@pytest.mark.asyncio
async def test_given_saved_preference_when_clear_then_get_returns_none(tmp_path: Path):
	# given
	path = tmp_path / "preferences.json"
	prefs = JsonUserPreferences(path)
	prefs.set_compress_media(False)
	assert prefs.get_compress_media() is False
	# when
	ClearUserPreferences(prefs).run()
	# then
	assert prefs.get_compress_media() is None
	assert not path.exists()


@pytest.mark.asyncio
async def test_given_library_files_when_reset_then_buckets_and_caches_empty(tmp_path: Path):
	# given
	library = tmp_path / "lib"
	fs = LocalFileSystem()
	index = SqliteGalleryIndex()
	fs.ensure_library_folders(str(library))
	(library / LibraryFolder.ORIGINALS.value / "a.jpg").write_bytes(b"a")
	(library / LibraryFolder.PROCESSED.value / "b.avif").write_bytes(b"b")
	(library / LibraryFolder.ERROR.value / "c.jpg").write_bytes(b"c")
	(library / ".thumbnails" / "b.avif.jpg").parent.mkdir(parents=True, exist_ok=True)
	(library / ".thumbnails" / "b.avif.jpg").write_bytes(b"t")
	(library / ".exports" / "b.avif.jpg").parent.mkdir(parents=True, exist_ok=True)
	(library / ".exports" / "b.avif.jpg").write_bytes(b"e")
	Path(gallery_index_path(str(library))).write_bytes(b"sqlite")
	# when
	await ResetLibrary(fs, index).run(str(library))
	# then
	assert fs.count_files_in_folder(str(library), LibraryFolder.ORIGINALS) == 0
	assert fs.count_files_in_folder(str(library), LibraryFolder.PROCESSED) == 0
	assert fs.count_files_in_folder(str(library), LibraryFolder.ERROR) == 0
	assert not (library / ".thumbnails").exists()
	assert not (library / ".exports").exists()
	assert not Path(gallery_index_path(str(library))).exists()
	assert (library / LibraryFolder.PROCESSED.value).is_dir()


@pytest.mark.asyncio
async def test_given_open_sqlite_index_when_reset_then_index_file_removed(tmp_path: Path):
	# given — mirrors production: gallery browse keeps a live connection cached
	library = tmp_path / "lib"
	fs = LocalFileSystem()
	index = SqliteGalleryIndex()
	fs.ensure_library_folders(str(library))
	await index.apply_sync(
		str(library),
		upserts=[
			GalleryIndexRow(
				relative_path="b.avif",
				captured_at=datetime(2025, 9, 4),
				kind=MediaKind.IMAGE,
				mtime=1.0,
				size=10,
			)
		],
		removed=[],
	)
	assert await index.count(str(library)) == 1
	assert Path(gallery_index_path(str(library))).is_file()
	# when
	await ResetLibrary(fs, index).run(str(library))
	# then
	assert not Path(gallery_index_path(str(library))).exists()
	assert not (library / ".index.sqlite-wal").exists()
	assert not (library / ".index.sqlite-shm").exists()
	assert await index.count(str(library)) == 0
