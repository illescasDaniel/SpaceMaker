from __future__ import annotations

from typing import Literal

from spacemaker.domain.gallery import GalleryItem
from spacemaker.domain.gallery_index import GalleryCursor, GalleryPage
from spacemaker.ports.outbound.gallery_index import GalleryIndexPort


class GenerateGallery:
	def __init__(self, index: GalleryIndexPort) -> None:
		self._index = index

	async def list_timeline_page(self, library_root: str, *, cursor: str | None, limit: int) -> GalleryPage:
		decoded = GalleryCursor.decode(cursor) if cursor else None
		return await self._index.page(library_root, cursor=decoded, limit=limit)

	async def calendar_days(self, library_root: str, year: int, month: int) -> list[int]:
		return await self._index.days_with_media(library_root, year, month)

	async def list_day(self, library_root: str, year: int, month: int, day: int) -> list[GalleryItem]:
		return await self._index.items_for_day(library_root, year, month, day)

	async def neighbor(
		self, library_root: str, relative_path: str, *, direction: Literal["prev", "next"]
	) -> GalleryItem | None:
		return await self._index.neighbor(library_root, relative_path, direction=direction)
