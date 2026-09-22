from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class GalleryItem:
	relative_path: str
	captured_at: datetime


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
