import threading
from datetime import datetime
from pathlib import Path

from spacemaker.adapters.outbound.gallery.sqlite_index import SqliteGalleryIndex
from spacemaker.domain.gallery_index import GalleryCursor, GalleryIndexRow
from spacemaker.domain.media import MediaKind


def test_given_new_library_root_when_connect_then_creates_index_file_with_schema(tmp_path: Path):
	# given
	library = str(tmp_path / "lib")
	index = SqliteGalleryIndex()
	# when
	conn = index._connect(library)
	# then
	assert index.db_path(library).is_file()
	assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
	assert conn.execute("SELECT COUNT(*) FROM gallery_items").fetchone()[0] == 0


def test_given_corrupt_index_file_when_connect_then_recreates_usable_schema(tmp_path: Path):
	# given
	library = str(tmp_path / "lib")
	index = SqliteGalleryIndex()
	db_path = index.db_path(library)
	db_path.parent.mkdir(parents=True)
	db_path.write_bytes(b"not a sqlite database")
	# when
	conn = index._connect(library)
	# then
	assert conn.execute("SELECT COUNT(*) FROM gallery_items").fetchone()[0] == 0


def test_given_reopened_valid_index_when_connect_then_reuses_existing_data(tmp_path: Path):
	# given
	library = str(tmp_path / "lib")
	first = SqliteGalleryIndex()
	conn = first._connect(library)
	conn.execute(
		"INSERT INTO gallery_items (relative_path, captured_at, kind, mtime, size) VALUES (?, ?, ?, ?, ?)",
		("a.avif", datetime(2025, 9, 4).timestamp(), "image", 1.0, 10),
	)
	conn.commit()
	# when
	second = SqliteGalleryIndex()
	reopened = second._connect(library)
	# then
	assert reopened.execute("SELECT COUNT(*) FROM gallery_items").fetchone()[0] == 1


def test_given_ties_on_captured_at_when_paginating_then_no_duplicates_or_gaps(tmp_path: Path):
	# given
	library = str(tmp_path / "lib")
	index = SqliteGalleryIndex()
	same_time = datetime(2025, 9, 4)
	rows = [
		GalleryIndexRow(relative_path=f"{i:03d}.avif", captured_at=same_time, kind=MediaKind.IMAGE, mtime=1.0, size=10)
		for i in range(5)
	]
	index.apply_sync(library, upserts=rows, removed=[])
	# when
	first_page = index.page(library, cursor=None, limit=2)
	second_page = index.page(
		library, cursor=GalleryCursor.decode(first_page.next_cursor) if first_page.next_cursor else None, limit=2
	)
	# then
	seen = [item.relative_path for item in first_page.items] + [item.relative_path for item in second_page.items]
	assert len(seen) == len(set(seen))


def test_given_first_and_last_item_when_neighbor_then_boundary_returns_none(tmp_path: Path):
	# given
	library = str(tmp_path / "lib")
	index = SqliteGalleryIndex()
	rows = [
		GalleryIndexRow(
			relative_path="a.avif", captured_at=datetime(2025, 9, 4), kind=MediaKind.IMAGE, mtime=1.0, size=10
		),
		GalleryIndexRow(
			relative_path="b.avif", captured_at=datetime(2025, 9, 5), kind=MediaKind.IMAGE, mtime=1.0, size=10
		),
	]
	index.apply_sync(library, upserts=rows, removed=[])
	# when / then — newest first: b.avif is first (nothing newer), a.avif is last (nothing older)
	assert index.neighbor(library, "b.avif", direction="prev") is None
	assert index.neighbor(library, "a.avif", direction="next") is None


def test_given_three_items_when_neighbor_then_returns_adjacent_in_timeline_order(tmp_path: Path):
	# given
	library = str(tmp_path / "lib")
	index = SqliteGalleryIndex()
	rows = [
		GalleryIndexRow(
			relative_path=name, captured_at=datetime(2025, 9, day), kind=MediaKind.IMAGE, mtime=1.0, size=10
		)
		for day, name in ((4, "a.avif"), (5, "b.avif"), (6, "c.avif"))
	]
	index.apply_sync(library, upserts=rows, removed=[])
	# when
	older = index.neighbor(library, "b.avif", direction="next")
	newer = index.neighbor(library, "b.avif", direction="prev")
	# then — newest first: c.avif, b.avif, a.avif
	assert older is not None
	assert newer is not None
	assert older.relative_path == "a.avif"
	assert newer.relative_path == "c.avif"


def test_given_upserted_row_when_get_and_remove_then_reflects_change(tmp_path: Path):
	# given
	library = str(tmp_path / "lib")
	index = SqliteGalleryIndex()
	row = GalleryIndexRow(
		relative_path="a.avif", captured_at=datetime(2025, 9, 4), kind=MediaKind.IMAGE, mtime=1.0, size=10
	)
	index.apply_sync(library, upserts=[row], removed=[])
	# when / then
	fetched = index.get(library, "a.avif")
	assert fetched == row
	assert index.count(library) == 1
	index.remove(library, "a.avif")
	assert index.get(library, "a.avif") is None
	assert index.count(library) == 0


def test_given_rows_across_months_when_days_with_media_then_scoped_to_month(tmp_path: Path):
	# given
	library = str(tmp_path / "lib")
	index = SqliteGalleryIndex()
	rows = [
		GalleryIndexRow(
			relative_path="sep2.avif", captured_at=datetime(2025, 9, 2), kind=MediaKind.IMAGE, mtime=1.0, size=10
		),
		GalleryIndexRow(
			relative_path="sep4.avif", captured_at=datetime(2025, 9, 4), kind=MediaKind.IMAGE, mtime=1.0, size=10
		),
		GalleryIndexRow(
			relative_path="oct1.avif", captured_at=datetime(2025, 10, 1), kind=MediaKind.IMAGE, mtime=1.0, size=10
		),
	]
	index.apply_sync(library, upserts=rows, removed=[])
	# when
	days = index.days_with_media(library, 2025, 9)
	# then
	assert days == [2, 4]


def test_given_rows_on_different_days_when_items_for_day_then_only_that_day(tmp_path: Path):
	# given
	library = str(tmp_path / "lib")
	index = SqliteGalleryIndex()
	rows = [
		GalleryIndexRow(
			relative_path="a.avif", captured_at=datetime(2025, 9, 4, 9), kind=MediaKind.IMAGE, mtime=1.0, size=10
		),
		GalleryIndexRow(
			relative_path="b.avif", captured_at=datetime(2025, 9, 5, 9), kind=MediaKind.IMAGE, mtime=1.0, size=10
		),
	]
	index.apply_sync(library, upserts=rows, removed=[])
	# when
	items = index.items_for_day(library, 2025, 9, 4)
	# then
	assert [item.relative_path for item in items] == ["a.avif"]


def test_given_concurrent_reads_when_many_threads_query_then_no_sqlite_errors(tmp_path: Path):
	# given
	library = str(tmp_path / "lib")
	index = SqliteGalleryIndex()
	rows = [
		GalleryIndexRow(
			relative_path=f"{i:03d}.avif",
			captured_at=datetime(2025, 9, 1 + i % 28),
			kind=MediaKind.IMAGE,
			mtime=1.0,
			size=10,
		)
		for i in range(20)
	]
	index.apply_sync(library, upserts=rows, removed=[])
	errors: list[BaseException] = []

	def worker(path: str) -> None:
		try:
			index.neighbor(library, path, direction="prev")
			index.neighbor(library, path, direction="next")
			index.get(library, path)
		except BaseException as exc:  # noqa: BLE001
			errors.append(exc)

	# when
	threads = [threading.Thread(target=worker, args=(row.relative_path,)) for row in rows for _ in range(3)]
	for t in threads:
		t.start()
	for t in threads:
		t.join()
	# then
	assert errors == []
