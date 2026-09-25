from datetime import datetime

from spacemaker.domain.gallery_index import FileStat, GalleryCursor, plan_index_sync


def test_given_identical_dicts_when_plan_index_sync_then_empty_plan():
	# given
	stats = {"a.avif": FileStat(mtime=1.0, size=10)}
	# when
	plan = plan_index_sync(indexed=stats, on_disk=stats)
	# then
	assert plan.is_empty


def test_given_new_path_on_disk_when_plan_index_sync_then_added():
	# given
	indexed: dict[str, FileStat] = {}
	on_disk = {"a.avif": FileStat(mtime=1.0, size=10)}
	# when
	plan = plan_index_sync(indexed=indexed, on_disk=on_disk)
	# then
	assert plan.added == ("a.avif",)
	assert plan.changed == ()
	assert plan.removed == ()


def test_given_indexed_path_missing_on_disk_when_plan_index_sync_then_removed():
	# given
	indexed = {"a.avif": FileStat(mtime=1.0, size=10)}
	on_disk: dict[str, FileStat] = {}
	# when
	plan = plan_index_sync(indexed=indexed, on_disk=on_disk)
	# then
	assert plan.removed == ("a.avif",)
	assert plan.added == ()
	assert plan.changed == ()


def test_given_differing_mtime_when_plan_index_sync_then_changed():
	# given
	indexed = {"a.avif": FileStat(mtime=1.0, size=10)}
	on_disk = {"a.avif": FileStat(mtime=2.0, size=10)}
	# when
	plan = plan_index_sync(indexed=indexed, on_disk=on_disk)
	# then
	assert plan.changed == ("a.avif",)
	assert plan.added == ()
	assert plan.removed == ()


def test_given_differing_size_same_mtime_when_plan_index_sync_then_changed():
	# given
	indexed = {"a.avif": FileStat(mtime=1.0, size=10)}
	on_disk = {"a.avif": FileStat(mtime=1.0, size=20)}
	# when
	plan = plan_index_sync(indexed=indexed, on_disk=on_disk)
	# then
	assert plan.changed == ("a.avif",)


def test_given_matching_stats_when_plan_index_sync_then_not_flagged_changed():
	# given
	indexed = {"a.avif": FileStat(mtime=1.0, size=10), "b.avif": FileStat(mtime=2.0, size=20)}
	on_disk = {"a.avif": FileStat(mtime=1.0, size=10), "b.avif": FileStat(mtime=2.0, size=20)}
	# when
	plan = plan_index_sync(indexed=indexed, on_disk=on_disk)
	# then
	assert plan.is_empty


def test_given_cursor_when_encode_and_decode_then_round_trips():
	# given
	cursor = GalleryCursor(captured_at=datetime(2025, 9, 4, 10, 30), relative_path="a.avif")
	# when
	decoded = GalleryCursor.decode(cursor.encode())
	# then
	assert decoded.relative_path == cursor.relative_path
	assert decoded.captured_at == cursor.captured_at
