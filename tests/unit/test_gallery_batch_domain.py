import pytest

from spacemaker.domain.gallery_batch import (
	BATCH_ARTIFACT_MAX_AGE_SECONDS,
	MAX_GALLERY_BATCH_ITEMS,
	BatchConvertItemResult,
	BatchConvertOutcome,
	BatchProgress,
	BatchTooLargeError,
	UnsafeBatchPathError,
	assign_zip_entry_names,
	is_batch_artifact_expired,
	normalize_batch_paths,
	required_free_bytes,
	zip_entry_name,
)
from spacemaker.domain.gallery_export import ExportFormat


def test_given_duplicate_paths_when_normalize_then_first_seen_order_without_duplicates() -> None:
	# given
	paths = ["b.avif", "a.avif", "b.avif"]
	# when
	result = normalize_batch_paths(paths)
	# then
	assert result == ("b.avif", "a.avif")


@pytest.mark.parametrize("bad", ["../outside.jpg", "/etc/passwd", "C:\\x.jpg", "a/../../b.jpg", ""])
def test_given_unsafe_path_when_normalize_then_rejects_whole_request(bad: str) -> None:
	# given
	paths = ["ok.avif", bad]
	# when
	# then
	with pytest.raises(UnsafeBatchPathError):
		normalize_batch_paths(paths)


def test_given_more_than_limit_distinct_paths_when_normalize_then_too_large() -> None:
	# given
	paths = [f"{i}.avif" for i in range(MAX_GALLERY_BATCH_ITEMS + 1)]
	# when
	# then
	with pytest.raises(BatchTooLargeError):
		normalize_batch_paths(paths)


def test_given_limit_paths_with_duplicates_when_normalize_then_counts_distinct_only() -> None:
	# given
	paths = [f"{i}.avif" for i in range(MAX_GALLERY_BATCH_ITEMS)] * 2
	# when
	result = normalize_batch_paths(paths)
	# then
	assert len(result) == MAX_GALLERY_BATCH_ITEMS


def test_given_converted_and_passthrough_when_zip_entry_name_then_extension_only_for_converted() -> None:
	# given
	# when
	converted = zip_entry_name("2025/a.avif", ExportFormat.JPEG)
	video = zip_entry_name("2025/clip.av1.mp4", ExportFormat.H264_AAC)
	passthrough = zip_entry_name("2025/b.jpg", None)
	# then
	assert converted == "2025/a.avif.jpg"
	assert video == "2025/clip.av1.mp4.mp4"
	assert passthrough == "2025/b.jpg"


def test_given_same_stem_in_two_years_when_assign_names_then_entries_are_unique() -> None:
	# given
	results = [
		_ok("2025/a.avif", ExportFormat.JPEG),
		_ok("2024/a.avif", ExportFormat.JPEG),
	]
	# when
	named = assign_zip_entry_names(results)
	# then
	names = [r.archive_name for r in named]
	assert sorted(names) == ["2024/a.avif.jpg", "2025/a.avif.jpg"]


def test_given_passthrough_colliding_with_converted_when_assign_names_then_disambiguated() -> None:
	# given
	results = [
		_ok("x.avif", ExportFormat.JPEG),
		_ok("x.avif.jpg", None, outcome=BatchConvertOutcome.PASSED_THROUGH),
	]
	# when
	named = assign_zip_entry_names(results)
	# then
	names = [r.archive_name for r in named]
	assert len(set(names)) == 2
	assert all(".." not in n and not n.startswith("/") for n in names)


def test_given_skipped_item_when_assign_names_then_excluded() -> None:
	# given
	results = [
		_ok("a.avif", ExportFormat.JPEG),
		BatchConvertItemResult("b.avif", BatchConvertOutcome.SKIPPED, reason="bad"),
	]
	# when
	named = assign_zip_entry_names(results)
	# then
	assert [r.relative_path for r in named] == ["a.avif"]


def test_given_sizes_when_required_free_bytes_then_sums_both_groups() -> None:
	# given
	# when
	needed = required_free_bytes([100, 200], [50])
	# then
	assert needed == 350


def test_given_age_when_expired_check_then_boundary_is_24_hours() -> None:
	# given
	# when
	# then
	assert is_batch_artifact_expired(BATCH_ARTIFACT_MAX_AGE_SECONDS - 1) is False
	assert is_batch_artifact_expired(BATCH_ARTIFACT_MAX_AGE_SECONDS) is True


def test_given_progress_when_overall_percent_then_blends_item_index_and_item_percent() -> None:
	# given
	progress = BatchProgress(item_index=1, item_count=4, item_percent=50)
	# when
	# then
	assert progress.overall_percent == 37
	assert BatchProgress(item_index=0, item_count=0, item_percent=0).overall_percent == 100


def _ok(
	relative: str,
	fmt: ExportFormat | None,
	*,
	outcome: BatchConvertOutcome = BatchConvertOutcome.CONVERTED,
) -> BatchConvertItemResult:
	return BatchConvertItemResult(relative, outcome, export_format=fmt, output_path=f"/abs/{relative}")
