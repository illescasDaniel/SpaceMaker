from dataclasses import replace
from datetime import datetime

import pytest

from spacemaker.domain.gallery_batch import (
	BATCH_ARTIFACT_MAX_AGE_SECONDS,
	MAX_GALLERY_BATCH_ITEMS,
	BatchConvertItemResult,
	BatchConvertOutcome,
	BatchProgress,
	BatchTooLargeError,
	UnsafeBatchPathError,
	archive_file_name,
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


def test_given_converted_and_passthrough_when_zip_entry_name_then_year_month_layout() -> None:
	# given
	when = datetime(2026, 9, 3)
	# when
	converted = zip_entry_name("DCIM/100APPLE/a.avif", ExportFormat.JPEG, when)
	video = zip_entry_name("Camera/clip.av1.mp4", ExportFormat.H264_AAC, datetime(2025, 1, 10))
	passthrough = zip_entry_name("b.jpg", None, when)
	# then
	assert converted == "2026/09/a.avif.jpg"
	assert video == "2025/01/clip.av1.mp4.mp4"
	assert passthrough == "2026/09/b.jpg"


def test_given_same_name_in_one_month_when_assign_names_then_suffix_disambiguates() -> None:
	# given
	when = datetime(2025, 3, 1)
	results = [
		replace(_ok("A/a.avif", ExportFormat.JPEG), captured_at=when),
		replace(_ok("B/a.avif", ExportFormat.JPEG), captured_at=when),
	]
	# when
	named = assign_zip_entry_names(results)
	# then
	assert [r.archive_name for r in named] == ["2025/03/a.avif.jpg", "2025/03/a.avif_2.jpg"]


def test_given_same_name_in_two_months_when_assign_names_then_no_suffix() -> None:
	# given
	results = [
		replace(_ok("a.avif", ExportFormat.JPEG), captured_at=datetime(2025, 3, 1)),
		replace(_ok("x/a.avif", ExportFormat.JPEG), captured_at=datetime(2024, 3, 1)),
	]
	# when
	named = assign_zip_entry_names(results)
	# then
	assert sorted(r.archive_name for r in named) == ["2024/03/a.avif.jpg", "2025/03/a.avif.jpg"]


def test_given_job_id_when_archive_file_name_then_spacemaker_media_prefix() -> None:
	# given
	# when
	name = archive_file_name("abc123")
	# then
	assert name == "spacemaker-media-abc123.zip"


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
