from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from spacemaker.domain.media import MediaKind, media_kind_for_filename


@dataclass(frozen=True, slots=True)
class GalleryItem:
	relative_path: str
	captured_at: datetime
	kind: MediaKind


@dataclass(frozen=True, slots=True)
class MonthGroup:
	year: int
	month: int
	items: tuple[GalleryItem, ...]


def group_timeline(items: list[GalleryItem]) -> list[MonthGroup]:
	sorted_items = sorted(items, key=lambda i: i.captured_at, reverse=True)
	buckets: dict[tuple[int, int], list[GalleryItem]] = {}
	for item in sorted_items:
		key = (item.captured_at.year, item.captured_at.month)
		buckets.setdefault(key, []).append(item)
	keys = sorted(buckets.keys(), reverse=True)
	return [MonthGroup(year=y, month=m, items=tuple(buckets[(y, m)])) for y, m in keys]


def days_with_media(items: list[GalleryItem]) -> frozenset[tuple[int, int, int]]:
	return frozenset((i.captured_at.year, i.captured_at.month, i.captured_at.day) for i in items)


def days_in_month(items: list[GalleryItem], year: int, month: int) -> frozenset[int]:
	return frozenset(i.captured_at.day for i in items if i.captured_at.year == year and i.captured_at.month == month)


def items_for_day(items: list[GalleryItem], year: int, month: int, day: int) -> list[GalleryItem]:
	return [
		i for i in items if i.captured_at.year == year and i.captured_at.month == month and i.captured_at.day == day
	]


def gallery_item(relative_path: str, captured_at: datetime) -> GalleryItem:
	return GalleryItem(
		relative_path=relative_path,
		captured_at=captured_at,
		kind=media_kind_for_filename(relative_path),
	)
