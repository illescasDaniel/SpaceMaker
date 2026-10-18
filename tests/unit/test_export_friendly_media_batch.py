import os
from pathlib import Path

import pytest
from tests.unit.fakes import FakeArchiveWriter, FakeDiskSpace, FakeMediaConverter, FakeMediaProbe

from spacemaker.adapters.outbound.filesystem.local import LocalFileSystem
from spacemaker.application.export_friendly_media import ExportFriendlyMedia
from spacemaker.application.export_friendly_media_batch import ExportFriendlyMediaBatch
from spacemaker.domain.gallery_batch import (
	BATCH_ARTIFACT_MAX_AGE_SECONDS,
	BatchConvertOutcome,
	BatchProgress,
	BatchTooLargeError,
	CpuEncodeConfirmationRequired,
	InsufficientDiskSpaceError,
	UnsafeBatchPathError,
	VideoExportEncoder,
)
from spacemaker.domain.gallery_cache_paths import batch_export_job_dir, export_cache_path
from spacemaker.domain.gallery_export import ExportFormat
from spacemaker.domain.library import LibraryFolder
from spacemaker.domain.web_compat import VideoProbe


FRIENDLY = VideoProbe(container_ext="mp4", video_codec="h264", audio_codec="aac", bitrate_bps=2_000_000)


class Env:
	def __init__(self, tmp_path, *, encoder: VideoExportEncoder = VideoExportEncoder.HARDWARE_H264) -> None:
		self.library = str(tmp_path / "lib")
		self.fs = LocalFileSystem()
		self.fs.ensure_library_folders(self.library)
		self.converter = FakeMediaConverter(friendly_encoder=encoder)
		self.probe = FakeMediaProbe()
		self.disk = FakeDiskSpace()
		self.archive = FakeArchiveWriter()
		export = ExportFriendlyMedia(self.fs, self.converter, self.probe)
		self.use_case = ExportFriendlyMediaBatch(export, self.converter, self.probe, self.fs, self.disk, self.archive)

	def add(self, rel: str, size: int = 100) -> str:
		path = self.fs.library_path(self.library, LibraryFolder.PROCESSED, rel)
		Path(path).parent.mkdir(parents=True, exist_ok=True)
		Path(path).write_bytes(b"x" * size)
		return path

	def run(self, paths, *, allow_cpu: bool = False, on_progress=None):
		return self.use_case.run(self.library, "job1", paths, allow_cpu_encode=allow_cpu, on_progress=on_progress)


def test_given_photos_and_video_when_convert_then_each_encoded_and_one_zip_written(tmp_path) -> None:
	# given
	env = Env(tmp_path)
	env.add("a.avif")
	env.add("b.png")
	env.add("c.av1.mp4")
	progress: list[BatchProgress] = []
	# when
	result = env.run(["a.avif", "b.png", "c.av1.mp4"], on_progress=progress.append)
	# then
	assert [r.outcome for r in result.results] == [BatchConvertOutcome.CONVERTED] * 3
	assert len(env.converter.encoded_jpegs) == 2
	assert len(env.converter.encoded_h264) == 1
	assert env.converter.h264_use_cpu_flags == [False]
	assert len(env.archive.written) == 1
	destination, entries = env.archive.written[0]
	assert destination.startswith(batch_export_job_dir(env.library, "job1"))
	assert sorted(e.entry_name for e in entries) == ["a.avif.jpg", "b.png.jpg", "c.av1.mp4.mp4"]
	assert result.archive_path == destination
	assert progress[-1].item_index >= 2


def test_given_originals_when_convert_then_processed_files_unchanged(tmp_path) -> None:
	# given
	env = Env(tmp_path)
	source = env.add("a.avif", size=321)
	# when
	env.run(["a.avif"])
	# then
	assert Path(source).read_bytes() == b"x" * 321


def test_given_already_friendly_items_when_convert_then_passed_through_without_encode(tmp_path) -> None:
	# given
	env = Env(tmp_path)
	jpg = env.add("a.jpg")
	mp4 = env.add("b.mp4")
	env.probe.videos[mp4] = FRIENDLY
	# when
	result = env.run(["a.jpg", "b.mp4"])
	# then
	assert [r.outcome for r in result.results] == [BatchConvertOutcome.PASSED_THROUGH] * 2
	assert env.converter.encoded_jpegs == []
	assert env.converter.encoded_h264 == []
	_dest, entries = env.archive.written[0]
	assert {e.source_path for e in entries} == {str(Path(jpg).resolve()), str(Path(mp4).resolve())}


def test_given_fresh_export_cache_when_convert_then_not_reencoded(tmp_path) -> None:
	# given
	env = Env(tmp_path)
	source = env.add("a.avif")
	cache = Path(export_cache_path(env.library, "a.avif", ExportFormat.JPEG))
	cache.parent.mkdir(parents=True, exist_ok=True)
	cache.write_bytes(b"cached")
	os.utime(cache, (Path(source).stat().st_mtime + 10,) * 2)
	# when
	result = env.run(["a.avif"])
	# then
	assert env.converter.encoded_jpegs == []
	assert result.results[0].outcome is BatchConvertOutcome.CONVERTED
	_dest, entries = env.archive.written[0]
	assert entries[0].source_path == str(cache.resolve())


def test_given_one_item_fails_when_convert_then_others_zipped_and_failure_listed(tmp_path) -> None:
	# given
	env = Env(tmp_path)
	bad = env.add("bad.avif")
	env.add("ok.avif")
	env.converter.fail_destinations.add(str(Path(bad).resolve()))
	# when
	result = env.run(["bad.avif", "ok.avif"])
	# then
	by_path = {r.relative_path: r for r in result.results}
	assert by_path["bad.avif"].outcome is BatchConvertOutcome.SKIPPED
	assert by_path["bad.avif"].reason
	assert by_path["ok.avif"].outcome is BatchConvertOutcome.CONVERTED
	_dest, entries = env.archive.written[0]
	assert [e.entry_name for e in entries] == ["ok.avif.jpg"]


def test_given_missing_source_when_convert_then_skipped_with_note(tmp_path) -> None:
	# given
	env = Env(tmp_path)
	env.add("ok.avif")
	# when
	result = env.run(["gone.avif", "ok.avif"])
	# then
	gone = next(r for r in result.results if r.relative_path == "gone.avif")
	assert gone.outcome is BatchConvertOutcome.SKIPPED
	assert gone.reason


def test_given_every_item_fails_when_convert_then_no_zip(tmp_path) -> None:
	# given
	env = Env(tmp_path)
	bad = env.add("bad.avif")
	env.converter.fail_destinations.add(str(Path(bad).resolve()))
	# when
	result = env.run(["bad.avif"])
	# then
	assert result.archive_path == ""
	assert env.archive.written == []
	assert result.results[0].outcome is BatchConvertOutcome.SKIPPED


def test_given_no_hardware_but_cpu_when_preflight_then_asks_once_with_video_count(tmp_path) -> None:
	# given
	env = Env(tmp_path, encoder=VideoExportEncoder.CPU_H264)
	env.add("a.avif")
	env.add("v1.av1.mp4")
	env.add("v2.mov")
	# when
	# then
	with pytest.raises(CpuEncodeConfirmationRequired) as info:
		env.use_case.preflight(env.library, ["a.avif", "v1.av1.mp4", "v2.mov"], allow_cpu_encode=False)
	assert info.value.video_count == 2


def test_given_cpu_confirmed_when_convert_then_videos_use_cpu_and_photos_unaffected(tmp_path) -> None:
	# given
	env = Env(tmp_path, encoder=VideoExportEncoder.CPU_H264)
	env.add("a.avif")
	env.add("v1.av1.mp4")
	env.use_case.preflight(env.library, ["a.avif", "v1.av1.mp4"], allow_cpu_encode=True)
	# when
	result = env.run(["a.avif", "v1.av1.mp4"], allow_cpu=True)
	# then
	assert env.converter.h264_use_cpu_flags == [True]
	assert len(env.converter.encoded_jpegs) == 1
	assert all(r.outcome is BatchConvertOutcome.CONVERTED for r in result.results)


def test_given_no_hardware_but_nothing_needs_encoding_when_preflight_then_no_prompt(tmp_path) -> None:
	# given
	env = Env(tmp_path, encoder=VideoExportEncoder.CPU_H264)
	env.add("a.avif")
	friendly = env.add("v.mp4")
	env.probe.videos[friendly] = FRIENDLY
	cached_src = env.add("c.av1.mp4")
	cache = Path(export_cache_path(env.library, "c.av1.mp4", ExportFormat.H264_AAC))
	cache.parent.mkdir(parents=True, exist_ok=True)
	cache.write_bytes(b"cached")
	os.utime(cache, (Path(cached_src).stat().st_mtime + 10,) * 2)
	# when
	paths = env.use_case.preflight(env.library, ["a.avif", "v.mp4", "c.av1.mp4"], allow_cpu_encode=False)
	# then
	assert paths == ("a.avif", "v.mp4", "c.av1.mp4")


def test_given_hardware_encoder_when_preflight_then_never_asks_for_cpu(tmp_path) -> None:
	# given
	env = Env(tmp_path, encoder=VideoExportEncoder.HARDWARE_H264)
	env.add("v.av1.mp4")
	# when
	paths = env.use_case.preflight(env.library, ["v.av1.mp4"], allow_cpu_encode=False)
	# then
	assert paths == ("v.av1.mp4",)


def test_given_no_encoder_at_all_when_convert_then_video_skipped_and_photos_zipped(tmp_path) -> None:
	# given
	env = Env(tmp_path, encoder=VideoExportEncoder.NONE)
	env.add("a.avif")
	env.add("v.av1.mp4")
	env.use_case.preflight(env.library, ["a.avif", "v.av1.mp4"], allow_cpu_encode=False)
	# when
	result = env.run(["a.avif", "v.av1.mp4"])
	# then
	by_path = {r.relative_path: r for r in result.results}
	assert by_path["a.avif"].outcome is BatchConvertOutcome.CONVERTED
	assert by_path["v.av1.mp4"].outcome is BatchConvertOutcome.SKIPPED
	assert "not available" in by_path["v.av1.mp4"].reason
	assert env.converter.encoded_h264 == []


def test_given_low_disk_space_when_preflight_then_fails_before_any_work(tmp_path) -> None:
	# given
	env = Env(tmp_path)
	env.add("a.avif", size=5000)
	env.disk.free = 10
	# when
	# then
	with pytest.raises(InsufficientDiskSpaceError):
		env.use_case.preflight(env.library, ["a.avif"], allow_cpu_encode=False)
	assert env.converter.encoded_jpegs == []


def test_given_unsafe_or_too_many_paths_when_preflight_then_rejected(tmp_path) -> None:
	# given
	env = Env(tmp_path)
	# when
	# then
	with pytest.raises(UnsafeBatchPathError):
		env.use_case.preflight(env.library, ["../x.avif"], allow_cpu_encode=False)
	with pytest.raises(BatchTooLargeError):
		env.use_case.preflight(env.library, [f"{i}.avif" for i in range(501)], allow_cpu_encode=False)


def test_given_batch_folders_when_delete_job_then_only_that_folder_removed(tmp_path) -> None:
	# given
	env = Env(tmp_path)
	keep = Path(batch_export_job_dir(env.library, "keep"))
	drop = Path(batch_export_job_dir(env.library, "drop"))
	for folder in (keep, drop):
		folder.mkdir(parents=True)
		(folder / "z.zip").write_bytes(b"zip")
	# when
	env.use_case.delete_job(env.library, "drop")
	# then
	assert keep.is_dir()
	assert not drop.exists()


def test_given_old_and_new_folders_when_sweep_then_only_expired_not_kept_are_removed(tmp_path) -> None:
	# given
	env = Env(tmp_path)
	now = 2_000_000_000.0
	old = Path(batch_export_job_dir(env.library, "old"))
	fresh = Path(batch_export_job_dir(env.library, "fresh"))
	running = Path(batch_export_job_dir(env.library, "running"))
	for folder, age in (
		(old, BATCH_ARTIFACT_MAX_AGE_SECONDS + 5),
		(fresh, 10),
		(running, BATCH_ARTIFACT_MAX_AGE_SECONDS + 5),
	):
		folder.mkdir(parents=True)
		zip_path = folder / "z.zip"
		zip_path.write_bytes(b"zip")
		os.utime(zip_path, (now - age, now - age))
	# when
	env.use_case.sweep(env.library, now=now, keep_job_ids=frozenset({"running"}))
	# then
	assert not old.exists()
	assert fresh.is_dir()
	assert running.is_dir()


def test_given_restart_when_sweep_expire_all_then_every_folder_removed(tmp_path) -> None:
	# given
	env = Env(tmp_path)
	fresh = Path(batch_export_job_dir(env.library, "fresh"))
	fresh.mkdir(parents=True)
	(fresh / "z.zip").write_bytes(b"zip")
	# when
	env.use_case.sweep(env.library, now=2_000_000_000.0, expire_all=True)
	# then
	assert not fresh.exists()


def test_given_mixed_files_when_download_then_stored_files_zipped_unchanged_without_encoding(tmp_path) -> None:
	# given
	env = Env(tmp_path)
	stored = env.add("2025/a.avif")
	env.add("2025/c.av1.mp4")
	# when
	result = env.use_case.run_download(env.library, "job1", ["2025/a.avif", "2025/c.av1.mp4"])
	# then
	assert env.converter.encoded_jpegs == []
	assert env.converter.encoded_h264 == []
	assert [r.outcome for r in result.results] == [BatchConvertOutcome.PASSED_THROUGH] * 2
	entries = {e.entry_name: e.source_path for e in env.archive.written[-1][1]}
	assert entries["2025/a.avif"] == stored
	assert set(entries) == {"2025/a.avif", "2025/c.av1.mp4"}
	assert result.archive_path.endswith("SpaceMaker-export.zip")


def test_given_missing_file_when_download_then_skipped_and_others_zipped(tmp_path) -> None:
	# given
	env = Env(tmp_path)
	env.add("a.avif")
	# when
	result = env.use_case.run_download(env.library, "job1", ["a.avif", "gone.avif"])
	# then
	assert [r.outcome for r in result.results] == [BatchConvertOutcome.PASSED_THROUGH, BatchConvertOutcome.SKIPPED]
	assert result.results[1].reason


def test_given_all_missing_when_download_then_no_archive(tmp_path) -> None:
	# given
	env = Env(tmp_path)
	# when
	result = env.use_case.run_download(env.library, "job1", ["gone.avif"])
	# then
	assert result.archive_path == ""
	assert env.archive.written == []


def test_given_no_hw_encoder_when_preflight_download_then_no_cpu_confirmation(tmp_path) -> None:
	# given
	env = Env(tmp_path, encoder=VideoExportEncoder.CPU_H264)
	env.add("clip.mov")
	# when
	paths = env.use_case.preflight_download(env.library, ["clip.mov"])
	# then
	assert paths == ("clip.mov",)


def test_given_low_disk_or_unsafe_paths_when_preflight_download_then_rejected(tmp_path) -> None:
	# given
	env = Env(tmp_path)
	env.add("a.avif", size=5000)
	env.disk.free = 10
	# when
	# then
	with pytest.raises(InsufficientDiskSpaceError):
		env.use_case.preflight_download(env.library, ["a.avif"])
	with pytest.raises(UnsafeBatchPathError):
		env.use_case.preflight_download(env.library, ["../x.avif"])
	with pytest.raises(BatchTooLargeError):
		env.use_case.preflight_download(env.library, [f"{i}.avif" for i in range(501)])
