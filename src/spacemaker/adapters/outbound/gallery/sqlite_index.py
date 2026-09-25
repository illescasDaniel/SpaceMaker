from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from spacemaker.domain.gallery import GalleryItem
from spacemaker.domain.gallery_index import (
	FileStat,
	GalleryCursor,
	GalleryIndexRow,
	GalleryPage,
	from_epoch_seconds,
	to_epoch_seconds,
)
from spacemaker.domain.media import MediaKind


_SCHEMA_VERSION = 1

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS gallery_items (
	relative_path TEXT PRIMARY KEY,
	captured_at REAL NOT NULL,
	kind TEXT NOT NULL,
	mtime REAL NOT NULL,
	size INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_gallery_items_captured_at
	ON gallery_items (captured_at DESC, relative_path DESC);
"""


def _month_bounds(year: int, month: int) -> tuple[float, float]:
	start = datetime(year, month, 1)
	end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
	return to_epoch_seconds(start), to_epoch_seconds(end)


def _day_bounds(year: int, month: int, day: int) -> tuple[float, float]:
	start = datetime(year, month, day)
	end = start + timedelta(days=1)
	return to_epoch_seconds(start), to_epoch_seconds(end)


class SqliteGalleryIndex:
	def __init__(self) -> None:
		self._connections: dict[str, sqlite3.Connection] = {}
		# Reentrant: query methods hold this for their whole body (including the _connect()
		# call), which serializes access to sqlite3.Connection objects across threads —
		# required because concurrent execute() calls on the same connection from different
		# threads raise sqlite3.InterfaceError, even with check_same_thread=False.
		self._lock = threading.RLock()

	def db_path(self, library_root: str) -> Path:
		return Path(library_root) / ".index.sqlite"

	def _connect(self, library_root: str) -> sqlite3.Connection:
		with self._lock:
			conn = self._connections.get(library_root)
			if conn is not None:
				return conn
			conn = self._open(library_root)
			self._connections[library_root] = conn
			return conn

	def _open(self, library_root: str) -> sqlite3.Connection:
		db_path = self.db_path(library_root)
		db_path.parent.mkdir(parents=True, exist_ok=True)
		return self._open_and_ensure_schema(db_path)

	def _open_and_ensure_schema(self, db_path: Path) -> sqlite3.Connection:
		conn = sqlite3.connect(str(db_path), check_same_thread=False)
		self._enable_wal(conn)
		if self._schema_is_usable(conn):
			return conn
		# Derived cache: on corruption/version mismatch, drop and rebuild rather than migrate.
		conn.close()
		db_path.unlink(missing_ok=True)
		conn = sqlite3.connect(str(db_path), check_same_thread=False)
		self._enable_wal(conn)
		self._create_schema(conn)
		return conn

	def _enable_wal(self, conn: sqlite3.Connection) -> None:
		try:
			conn.execute("PRAGMA journal_mode=WAL")
		except sqlite3.DatabaseError:
			pass

	def _schema_is_usable(self, conn: sqlite3.Connection) -> bool:
		try:
			version = conn.execute("PRAGMA user_version").fetchone()[0]
		except sqlite3.DatabaseError:
			return False
		if version == 0:
			self._create_schema(conn)
			return True
		if version != _SCHEMA_VERSION:
			return False
		try:
			conn.execute("SELECT COUNT(*) FROM gallery_items")
		except sqlite3.DatabaseError:
			return False
		return True

	def _create_schema(self, conn: sqlite3.Connection) -> None:
		conn.executescript(_SCHEMA_SQL)
		conn.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
		conn.commit()

	def _row_from_record(self, record: tuple[str, float, str, float, int]) -> GalleryIndexRow:
		relative_path, captured_at, kind, mtime, size = record
		return GalleryIndexRow(
			relative_path=relative_path,
			captured_at=from_epoch_seconds(captured_at),
			kind=MediaKind(kind),
			mtime=mtime,
			size=size,
		)

	def snapshot_stats(self, library_root: str) -> dict[str, FileStat]:
		with self._lock:
			conn = self._connect(library_root)
			rows = conn.execute("SELECT relative_path, mtime, size FROM gallery_items").fetchall()
			return {relative_path: FileStat(mtime=mtime, size=size) for relative_path, mtime, size in rows}

	def apply_sync(self, library_root: str, *, upserts: list[GalleryIndexRow], removed: list[str]) -> None:
		with self._lock:
			conn = self._connect(library_root)
			with conn:
				if upserts:
					conn.executemany(
						"INSERT INTO gallery_items (relative_path, captured_at, kind, mtime, size) "
						"VALUES (?, ?, ?, ?, ?) "
						"ON CONFLICT(relative_path) DO UPDATE SET "
						"captured_at = excluded.captured_at, kind = excluded.kind, "
						"mtime = excluded.mtime, size = excluded.size",
						[
							(row.relative_path, to_epoch_seconds(row.captured_at), row.kind.value, row.mtime, row.size)
							for row in upserts
						],
					)
				if removed:
					conn.executemany(
						"DELETE FROM gallery_items WHERE relative_path = ?",
						[(relative_path,) for relative_path in removed],
					)

	def remove(self, library_root: str, relative_path: str) -> None:
		with self._lock:
			conn = self._connect(library_root)
			with conn:
				conn.execute("DELETE FROM gallery_items WHERE relative_path = ?", (relative_path,))

	def get(self, library_root: str, relative_path: str) -> GalleryIndexRow | None:
		with self._lock:
			conn = self._connect(library_root)
			record = conn.execute(
				"SELECT relative_path, captured_at, kind, mtime, size FROM gallery_items WHERE relative_path = ?",
				(relative_path,),
			).fetchone()
			return None if record is None else self._row_from_record(record)

	def page(self, library_root: str, *, cursor: GalleryCursor | None, limit: int) -> GalleryPage:
		with self._lock:
			conn = self._connect(library_root)
			if cursor is None:
				records = conn.execute(
					"SELECT relative_path, captured_at, kind, mtime, size FROM gallery_items "
					"ORDER BY captured_at DESC, relative_path DESC LIMIT ?",
					(limit + 1,),
				).fetchall()
			else:
				ts = to_epoch_seconds(cursor.captured_at)
				records = conn.execute(
					"SELECT relative_path, captured_at, kind, mtime, size FROM gallery_items "
					"WHERE (captured_at < ?) OR (captured_at = ? AND relative_path < ?) "
					"ORDER BY captured_at DESC, relative_path DESC LIMIT ?",
					(ts, ts, cursor.relative_path, limit + 1),
				).fetchall()
			page_records = records[:limit]
			next_cursor = None
			if len(records) > limit:
				last = self._row_from_record(page_records[-1])
				next_cursor = GalleryCursor(captured_at=last.captured_at, relative_path=last.relative_path).encode()
			items = tuple(self._row_from_record(record).as_item() for record in page_records)
			return GalleryPage(items=items, next_cursor=next_cursor)

	def days_with_media(self, library_root: str, year: int, month: int) -> list[int]:
		with self._lock:
			conn = self._connect(library_root)
			start, end = _month_bounds(year, month)
			records = conn.execute(
				"SELECT captured_at FROM gallery_items WHERE captured_at >= ? AND captured_at < ?",
				(start, end),
			).fetchall()
			return sorted({from_epoch_seconds(record[0]).day for record in records})

	def items_for_day(self, library_root: str, year: int, month: int, day: int) -> list[GalleryItem]:
		with self._lock:
			conn = self._connect(library_root)
			start, end = _day_bounds(year, month, day)
			records = conn.execute(
				"SELECT relative_path, captured_at, kind, mtime, size FROM gallery_items "
				"WHERE captured_at >= ? AND captured_at < ? "
				"ORDER BY captured_at DESC, relative_path DESC",
				(start, end),
			).fetchall()
			return [self._row_from_record(record).as_item() for record in records]

	def neighbor(
		self, library_root: str, relative_path: str, *, direction: Literal["prev", "next"]
	) -> GalleryItem | None:
		with self._lock:
			conn = self._connect(library_root)
			current = conn.execute(
				"SELECT captured_at FROM gallery_items WHERE relative_path = ?", (relative_path,)
			).fetchone()
			if current is None:
				return None
			captured_at = current[0]
			if direction == "next":
				record = conn.execute(
					"SELECT relative_path, captured_at, kind, mtime, size FROM gallery_items "
					"WHERE (captured_at < ?) OR (captured_at = ? AND relative_path < ?) "
					"ORDER BY captured_at DESC, relative_path DESC LIMIT 1",
					(captured_at, captured_at, relative_path),
				).fetchone()
			else:
				record = conn.execute(
					"SELECT relative_path, captured_at, kind, mtime, size FROM gallery_items "
					"WHERE (captured_at > ?) OR (captured_at = ? AND relative_path > ?) "
					"ORDER BY captured_at ASC, relative_path ASC LIMIT 1",
					(captured_at, captured_at, relative_path),
				).fetchone()
			return None if record is None else self._row_from_record(record).as_item()

	def count(self, library_root: str) -> int:
		with self._lock:
			conn = self._connect(library_root)
			return conn.execute("SELECT COUNT(*) FROM gallery_items").fetchone()[0]
