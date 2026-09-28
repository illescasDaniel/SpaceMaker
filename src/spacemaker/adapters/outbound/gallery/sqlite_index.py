from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal, TypeVar, cast

import aiosqlite

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


_SCHEMA_VERSION = 2
_T = TypeVar("_T")

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS gallery_items (
	relative_path TEXT PRIMARY KEY,
	captured_at REAL NOT NULL,
	kind TEXT NOT NULL,
	mtime REAL NOT NULL,
	size INTEGER NOT NULL,
	camera_make TEXT NOT NULL DEFAULT '',
	camera_model TEXT NOT NULL DEFAULT '',
	width INTEGER,
	height INTEGER,
	duration_seconds REAL,
	gps TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_gallery_items_captured_at
	ON gallery_items (captured_at DESC, relative_path DESC);
"""

_SELECT_ITEMS = (
	"SELECT relative_path, captured_at, kind, mtime, size, "
	"camera_make, camera_model, width, height, duration_seconds, gps "
	"FROM gallery_items"
)


def _month_bounds(year: int, month: int) -> tuple[float, float]:
	start = datetime(year, month, 1)
	end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
	return to_epoch_seconds(start), to_epoch_seconds(end)


def _day_bounds(year: int, month: int, day: int) -> tuple[float, float]:
	start = datetime(year, month, day)
	end = start + timedelta(days=1)
	return to_epoch_seconds(start), to_epoch_seconds(end)


class SqliteGalleryIndex:
	"""Async gallery index backed by aiosqlite.

	Connections are opened per operation (no cross-loop cache) so the same
	adapter instance can be used from the ASGI loop and from helper-thread
	``asyncio.run`` bridges without loop-affinity errors.
	"""

	def db_path(self, library_root: str) -> Path:
		return Path(library_root) / ".index.sqlite"

	async def _open(self, library_root: str) -> aiosqlite.Connection:
		db_path = self.db_path(library_root)
		db_path.parent.mkdir(parents=True, exist_ok=True)
		return await self._open_and_ensure_schema(db_path)

	async def _open_and_ensure_schema(self, db_path: Path) -> aiosqlite.Connection:
		conn = await aiosqlite.connect(str(db_path))
		await self._enable_wal(conn)
		if await self._schema_is_usable(conn):
			return conn
		await conn.close()
		db_path.unlink(missing_ok=True)
		conn = await aiosqlite.connect(str(db_path))
		await self._enable_wal(conn)
		await self._create_schema(conn)
		return conn

	async def _enable_wal(self, conn: aiosqlite.Connection) -> None:
		try:
			await conn.execute("PRAGMA journal_mode=WAL")
		except aiosqlite.DatabaseError:
			pass

	async def _schema_is_usable(self, conn: aiosqlite.Connection) -> bool:
		try:
			cursor = await conn.execute("PRAGMA user_version")
			row = await cursor.fetchone()
			version = 0 if row is None else int(row[0])
		except aiosqlite.DatabaseError:
			return False
		if version == 0:
			await self._create_schema(conn)
			return True
		if version != _SCHEMA_VERSION:
			return False
		try:
			await conn.execute("SELECT COUNT(*) FROM gallery_items")
		except aiosqlite.DatabaseError:
			return False
		return True

	async def _create_schema(self, conn: aiosqlite.Connection) -> None:
		await conn.executescript(_SCHEMA_SQL)
		await conn.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
		await conn.commit()

	async def _with_conn(self, library_root: str, body: Callable[[aiosqlite.Connection], Awaitable[_T]]) -> _T:
		conn = await self._open(library_root)
		try:
			return await body(conn)
		finally:
			await conn.close()

	def _row_from_record(self, record: Sequence[object]) -> GalleryIndexRow:
		row = cast(
			tuple[
				str,
				float,
				str,
				float,
				int,
				str | None,
				str | None,
				int | None,
				int | None,
				float | None,
				str | None,
			],
			tuple(record),
		)
		(
			relative_path,
			captured_at,
			kind,
			mtime,
			size,
			camera_make,
			camera_model,
			width,
			height,
			duration_seconds,
			gps,
		) = row
		return GalleryIndexRow(
			relative_path=relative_path,
			captured_at=from_epoch_seconds(captured_at),
			kind=MediaKind(kind),
			mtime=mtime,
			size=size,
			camera_make=camera_make or "",
			camera_model=camera_model or "",
			width=width,
			height=height,
			duration_seconds=duration_seconds,
			gps=gps or "",
		)

	async def snapshot_stats(self, library_root: str) -> dict[str, FileStat]:
		async def body(conn: aiosqlite.Connection) -> dict[str, FileStat]:
			cursor = await conn.execute("SELECT relative_path, mtime, size FROM gallery_items")
			rows = await cursor.fetchall()
			return {relative_path: FileStat(mtime=mtime, size=size) for relative_path, mtime, size in rows}

		return await self._with_conn(library_root, body)

	async def apply_sync(self, library_root: str, *, upserts: list[GalleryIndexRow], removed: list[str]) -> None:
		async def body(conn: aiosqlite.Connection) -> None:
			if upserts:
				await conn.executemany(
					"INSERT INTO gallery_items ("
					"relative_path, captured_at, kind, mtime, size, "
					"camera_make, camera_model, width, height, duration_seconds, gps"
					") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
					"ON CONFLICT(relative_path) DO UPDATE SET "
					"captured_at = excluded.captured_at, kind = excluded.kind, "
					"mtime = excluded.mtime, size = excluded.size, "
					"camera_make = excluded.camera_make, camera_model = excluded.camera_model, "
					"width = excluded.width, height = excluded.height, "
					"duration_seconds = excluded.duration_seconds, gps = excluded.gps",
					[
						(
							row.relative_path,
							to_epoch_seconds(row.captured_at),
							row.kind.value,
							row.mtime,
							row.size,
							row.camera_make,
							row.camera_model,
							row.width,
							row.height,
							row.duration_seconds,
							row.gps,
						)
						for row in upserts
					],
				)
			if removed:
				await conn.executemany(
					"DELETE FROM gallery_items WHERE relative_path = ?",
					[(relative_path,) for relative_path in removed],
				)
			await conn.commit()

		await self._with_conn(library_root, body)

	async def remove(self, library_root: str, relative_path: str) -> None:
		async def body(conn: aiosqlite.Connection) -> None:
			await conn.execute("DELETE FROM gallery_items WHERE relative_path = ?", (relative_path,))
			await conn.commit()

		await self._with_conn(library_root, body)

	async def get(self, library_root: str, relative_path: str) -> GalleryIndexRow | None:
		async def body(conn: aiosqlite.Connection) -> GalleryIndexRow | None:
			cursor = await conn.execute(
				_SELECT_ITEMS + " WHERE relative_path = ?",
				(relative_path,),
			)
			record = await cursor.fetchone()
			return None if record is None else self._row_from_record(record)

		return await self._with_conn(library_root, body)

	async def page(self, library_root: str, *, cursor: GalleryCursor | None, limit: int) -> GalleryPage:
		async def body(conn: aiosqlite.Connection) -> GalleryPage:
			if cursor is None:
				query = await conn.execute(
					_SELECT_ITEMS + " ORDER BY captured_at DESC, relative_path DESC LIMIT ?",
					(limit + 1,),
				)
			else:
				ts = to_epoch_seconds(cursor.captured_at)
				query = await conn.execute(
					_SELECT_ITEMS + " "
					"WHERE (captured_at < ?) OR (captured_at = ? AND relative_path < ?) "
					"ORDER BY captured_at DESC, relative_path DESC LIMIT ?",
					(ts, ts, cursor.relative_path, limit + 1),
				)
			records = list(await query.fetchall())
			page_records = records[:limit]
			next_cursor = None
			if len(records) > limit:
				last = self._row_from_record(page_records[-1])
				next_cursor = GalleryCursor(captured_at=last.captured_at, relative_path=last.relative_path).encode()
			items = tuple(self._row_from_record(record).as_item() for record in page_records)
			return GalleryPage(items=items, next_cursor=next_cursor)

		return await self._with_conn(library_root, body)

	async def days_with_media(self, library_root: str, year: int, month: int) -> list[int]:
		async def body(conn: aiosqlite.Connection) -> list[int]:
			start, end = _month_bounds(year, month)
			cursor = await conn.execute(
				"SELECT captured_at FROM gallery_items WHERE captured_at >= ? AND captured_at < ?",
				(start, end),
			)
			records = await cursor.fetchall()
			return sorted({from_epoch_seconds(record[0]).day for record in records})

		return await self._with_conn(library_root, body)

	async def items_for_day(self, library_root: str, year: int, month: int, day: int) -> list[GalleryItem]:
		async def body(conn: aiosqlite.Connection) -> list[GalleryItem]:
			start, end = _day_bounds(year, month, day)
			cursor = await conn.execute(
				_SELECT_ITEMS + " "
				"WHERE captured_at >= ? AND captured_at < ? "
				"ORDER BY captured_at DESC, relative_path DESC",
				(start, end),
			)
			records = await cursor.fetchall()
			return [self._row_from_record(record).as_item() for record in records]

		return await self._with_conn(library_root, body)

	async def neighbor(
		self, library_root: str, relative_path: str, *, direction: Literal["prev", "next"]
	) -> GalleryItem | None:
		async def body(conn: aiosqlite.Connection) -> GalleryItem | None:
			current_cursor = await conn.execute(
				"SELECT captured_at FROM gallery_items WHERE relative_path = ?", (relative_path,)
			)
			current = await current_cursor.fetchone()
			if current is None:
				return None
			captured_at = current[0]
			if direction == "next":
				query = await conn.execute(
					_SELECT_ITEMS + " "
					"WHERE (captured_at < ?) OR (captured_at = ? AND relative_path < ?) "
					"ORDER BY captured_at DESC, relative_path DESC LIMIT 1",
					(captured_at, captured_at, relative_path),
				)
			else:
				query = await conn.execute(
					_SELECT_ITEMS + " "
					"WHERE (captured_at > ?) OR (captured_at = ? AND relative_path > ?) "
					"ORDER BY captured_at ASC, relative_path ASC LIMIT 1",
					(captured_at, captured_at, relative_path),
				)
			record = await query.fetchone()
			return None if record is None else self._row_from_record(record).as_item()

		return await self._with_conn(library_root, body)

	async def count(self, library_root: str) -> int:
		async def body(conn: aiosqlite.Connection) -> int:
			cursor = await conn.execute("SELECT COUNT(*) FROM gallery_items")
			row = await cursor.fetchone()
			return 0 if row is None else int(row[0])

		return await self._with_conn(library_root, body)

	async def close(self, library_root: str) -> None:
		"""No-op for per-operation connections; kept for GalleryIndexPort / ResetLibrary."""
		_ = library_root
