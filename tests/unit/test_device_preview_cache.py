# Expected adapter for Phase 4 (filesystem implementation of ``DevicePreviewCachePort``):
#   module: spacemaker.adapters.outbound.media.file_device_preview_cache
#   class:  FileDevicePreviewCache(root: Path, max_bytes: int, now: Callable[[], float])
#   ``now`` is the injected recency source: the adapter stamps an entry's mtime (os.utime) from ``now()`` on put
#   and on a get hit, and evicts by smallest mtime.
# The format-version marker is NOT tested here: the version is part of the cache key
# (``device_preview_cache_key``), so the adapter does not own it and old entries simply never match.
import itertools
from pathlib import Path

from spacemaker.adapters.outbound.media.file_device_preview_cache import (
	FileDevicePreviewCache,
)
from spacemaker.domain.device_preview import CachedDevicePreview


KEY_A = "a" * 16
KEY_B = "b" * 16
KEY_C = "c" * 16


def _cache(root: Path, max_bytes: int) -> FileDevicePreviewCache:
	counter = itertools.count(1_000)
	return FileDevicePreviewCache(root, max_bytes, lambda: float(next(counter)))


def _stored_files(root: Path) -> list[Path]:
	return [p for p in root.rglob("*") if p.is_file()]


def test_given_empty_cache_when_get_then_none(tmp_path: Path) -> None:
	# given
	cache = _cache(tmp_path / "device-thumbs", 1000)
	# when
	result = cache.get(KEY_A)
	# then
	assert result is None


def test_given_put_when_get_then_same_bytes(tmp_path: Path) -> None:
	# given
	cache = _cache(tmp_path / "device-thumbs", 1000)
	# when
	cache.put(KEY_A, CachedDevicePreview(b"jpeg-a"))
	# then
	assert cache.get(KEY_A) == CachedDevicePreview(b"jpeg-a")
	assert cache.get(KEY_B) is None


def test_given_stored_entry_when_new_instance_on_same_root_then_still_served(tmp_path: Path) -> None:
	# given
	root = tmp_path / "device-thumbs"
	_cache(root, 1000).put(KEY_A, CachedDevicePreview(b"jpeg-a"))
	# when
	restarted = _cache(root, 1000)
	# then
	assert restarted.get(KEY_A) == CachedDevicePreview(b"jpeg-a")


def test_given_put_twice_when_get_then_latest_bytes(tmp_path: Path) -> None:
	# given
	cache = _cache(tmp_path / "device-thumbs", 1000)
	cache.put(KEY_A, CachedDevicePreview(b"old"))
	# when
	cache.put(KEY_A, CachedDevicePreview(b"newer"))
	# then
	assert cache.get(KEY_A) == CachedDevicePreview(b"newer")


def test_given_cache_over_limit_when_put_then_oldest_evicted_and_total_within_limit(tmp_path: Path) -> None:
	# given
	root = tmp_path / "device-thumbs"
	cache = _cache(root, 250)
	cache.put(KEY_A, CachedDevicePreview(b"a" * 100))
	cache.put(KEY_B, CachedDevicePreview(b"b" * 100))
	# when
	cache.put(KEY_C, CachedDevicePreview(b"c" * 100))
	# then
	assert cache.get(KEY_A) is None
	assert cache.get(KEY_B) == CachedDevicePreview(b"b" * 100)
	assert cache.get(KEY_C) == CachedDevicePreview(b"c" * 100)
	assert sum(p.stat().st_size for p in _stored_files(root)) <= 250


def test_given_entry_read_recently_when_eviction_then_least_recently_used_goes(tmp_path: Path) -> None:
	# given
	cache = _cache(tmp_path / "device-thumbs", 250)
	cache.put(KEY_A, CachedDevicePreview(b"a" * 100))
	cache.put(KEY_B, CachedDevicePreview(b"b" * 100))
	assert cache.get(KEY_A) == CachedDevicePreview(b"a" * 100)
	# when
	cache.put(KEY_C, CachedDevicePreview(b"c" * 100))
	# then
	assert cache.get(KEY_B) is None
	assert cache.get(KEY_A) == CachedDevicePreview(b"a" * 100)
	assert cache.get(KEY_C) == CachedDevicePreview(b"c" * 100)


def test_given_single_entry_larger_than_limit_when_put_then_new_entry_is_kept(tmp_path: Path) -> None:
	# given
	cache = _cache(tmp_path / "device-thumbs", 50)
	cache.put(KEY_A, CachedDevicePreview(b"a" * 30))
	# when
	cache.put(KEY_B, CachedDevicePreview(b"b" * 200))
	# then
	assert cache.get(KEY_B) == CachedDevicePreview(b"b" * 200)
	assert cache.get(KEY_A) is None


def test_given_put_when_done_then_only_the_entry_file_exists_no_temp_leftovers(tmp_path: Path) -> None:
	# given
	root = tmp_path / "device-thumbs"
	cache = _cache(root, 1000)
	# when
	cache.put(KEY_A, CachedDevicePreview(b"jpeg-a"))
	cache.put(KEY_B, CachedDevicePreview(b"jpeg-b"))
	# then
	files = _stored_files(root)
	assert len(files) == 2
	assert not [p for p in files if p.suffix == ".tmp"]


def test_given_leftover_partial_temp_file_when_get_then_never_served(tmp_path: Path) -> None:
	# given
	root = tmp_path / "device-thumbs"
	cache = _cache(root, 1000)
	cache.put(KEY_B, CachedDevicePreview(b"jpeg-b"))
	for name in (f"{KEY_A}.tmp", f"{KEY_A}.jpg.tmp", f"{KEY_A}.jpg.part.tmp"):
		(root / name).write_bytes(b"partial")
	# when
	result = cache.get(KEY_A)
	# then
	assert result is None
	assert cache.get(KEY_B) == CachedDevicePreview(b"jpeg-b")


# Video posters (SPEC "Video posters — strategy": the cache stores the JPEG and the duration; old v1 entries
# are a miss through the key version, covered in test_device_preview.py). Seam: the duration lives in a
# sidecar file next to the JPEG (counted in the size limit and evicted with it); photos have no duration.
def test_given_video_entry_with_duration_when_get_then_round_trips_both(tmp_path: Path) -> None:
	# given
	cache = _cache(tmp_path / "device-thumbs", 1000)
	# when
	cache.put(KEY_A, CachedDevicePreview(b"poster", 42.37))
	# then
	assert cache.get(KEY_A) == CachedDevicePreview(b"poster", 42.37)


def test_given_video_entry_when_new_instance_on_same_root_then_duration_survives(tmp_path: Path) -> None:
	# given
	root = tmp_path / "device-thumbs"
	_cache(root, 1000).put(KEY_A, CachedDevicePreview(b"poster", 3723.5))
	# when
	restarted = _cache(root, 1000)
	# then
	assert restarted.get(KEY_A) == CachedDevicePreview(b"poster", 3723.5)


def test_given_photo_entry_when_get_then_duration_none(tmp_path: Path) -> None:
	# given
	cache = _cache(tmp_path / "device-thumbs", 1000)
	# when
	cache.put(KEY_A, CachedDevicePreview(b"photo"))
	# then
	assert cache.get(KEY_A) == CachedDevicePreview(b"photo", None)


def test_given_video_entry_when_overwritten_without_duration_then_old_duration_not_served(tmp_path: Path) -> None:
	# given
	cache = _cache(tmp_path / "device-thumbs", 1000)
	cache.put(KEY_A, CachedDevicePreview(b"poster", 42.37))
	# when
	cache.put(KEY_A, CachedDevicePreview(b"poster-2", None))
	# then
	assert cache.get(KEY_A) == CachedDevicePreview(b"poster-2", None)


def test_given_duration_bytes_when_over_limit_then_counted_and_oldest_entry_evicted_with_its_duration(
	tmp_path: Path,
) -> None:
	# given
	root = tmp_path / "device-thumbs"
	cache = _cache(root, 205)  # two 100-byte posters fit only if their duration bytes are not counted
	cache.put(KEY_A, CachedDevicePreview(b"a" * 100, 42.37))
	# when
	cache.put(KEY_B, CachedDevicePreview(b"b" * 100, 42.37))
	# then
	assert cache.get(KEY_A) is None
	assert cache.get(KEY_B) == CachedDevicePreview(b"b" * 100, 42.37)
	assert sum(p.stat().st_size for p in _stored_files(root)) <= 205
	assert not [p for p in _stored_files(root) if p.name.startswith(KEY_A)]


def test_given_orphan_duration_sidecar_when_next_put_then_orphan_deleted(tmp_path: Path) -> None:
	# given
	root = tmp_path / "device-thumbs"
	root.mkdir()
	orphan = root / f"{KEY_C}.dur"
	orphan.write_text("12.5")
	cache = _cache(root, 1000)
	# when
	cache.put(KEY_A, CachedDevicePreview(b"jpeg"))
	# then
	assert not orphan.exists()
	assert [p.name for p in _stored_files(root)] == [f"{KEY_A}.jpg"]


def test_given_put_fails_when_video_then_no_sidecar_left_behind(tmp_path: Path) -> None:
	# given
	root = tmp_path / "device-thumbs"
	(root / f"{KEY_A}.jpg").mkdir(parents=True)  # renaming the JPEG onto a directory fails
	cache = _cache(root, 1000)
	# when
	cache.put(KEY_A, CachedDevicePreview(b"jpeg", 42.5))
	# then
	assert not (root / f"{KEY_A}.dur").exists()
	assert _stored_files(root) == []
