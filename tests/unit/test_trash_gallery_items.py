from pathlib import Path

import pytest
from tests.unit.fakes import FakeTrash

from spacemaker.adapters.outbound.filesystem.local import LocalFileSystem
from spacemaker.application.trash_gallery_items import TrashGalleryItems
from spacemaker.domain.gallery_batch import (
	MAX_GALLERY_BATCH_ITEMS,
	BatchTooLargeError,
	TrashOutcome,
	UnsafeBatchPathError,
)
from spacemaker.domain.gallery_cache_paths import export_cache_path, thumbnail_path
from spacemaker.domain.gallery_export import ExportFormat
from spacemaker.domain.library import LibraryFolder


def _library(tmp_path):
	library = str(tmp_path / "lib")
	fs = LocalFileSystem()
	fs.ensure_library_folders(library)
	return library, fs


def _processed(fs, library, rel: str) -> str:
	path = fs.library_path(library, LibraryFolder.PROCESSED, rel)
	Path(path).parent.mkdir(parents=True, exist_ok=True)
	Path(path).write_bytes(b"x")
	return path


def _caches(library, rel: str) -> tuple[Path, Path]:
	thumb = Path(thumbnail_path(library, rel))
	thumb.parent.mkdir(parents=True, exist_ok=True)
	thumb.write_bytes(b"t")
	export = Path(export_cache_path(library, rel, ExportFormat.JPEG))
	export.parent.mkdir(parents=True, exist_ok=True)
	export.write_bytes(b"e")
	return thumb, export


def test_given_selected_files_when_trash_then_moved_to_trash_and_caches_cleared(tmp_path) -> None:
	# given
	library, fs = _library(tmp_path)
	first = _processed(fs, library, "2025/a.avif")
	second = _processed(fs, library, "2025/b.avif")
	thumb, export = _caches(library, "2025/a.avif")
	trash = FakeTrash()
	use_case = TrashGalleryItems(fs, trash)
	# when
	results = use_case.run(library, ["2025/a.avif", "2025/b.avif"])
	# then
	assert [r.outcome for r in results] == [TrashOutcome.TRASHED, TrashOutcome.TRASHED]
	assert trash.trashed == [first, second]
	assert not thumb.exists()
	assert not export.exists()


def test_given_trash_fails_for_one_when_trash_then_file_untouched_and_others_proceed(tmp_path) -> None:
	# given
	library, fs = _library(tmp_path)
	bad = _processed(fs, library, "bad.avif")
	good = _processed(fs, library, "good.avif")
	thumb, _export = _caches(library, "bad.avif")
	trash = FakeTrash(fail_paths={bad})
	use_case = TrashGalleryItems(fs, trash)
	# when
	results = use_case.run(library, ["bad.avif", "good.avif"])
	# then
	by_path = {r.relative_path: r for r in results}
	assert by_path["bad.avif"].outcome is TrashOutcome.FAILED
	assert by_path["bad.avif"].reason
	assert by_path["good.avif"].outcome is TrashOutcome.TRASHED
	assert Path(bad).is_file()
	assert not Path(good).exists()
	assert thumb.exists()


def test_given_file_already_gone_when_trash_then_treated_as_done_and_caches_cleaned(tmp_path) -> None:
	# given
	library, fs = _library(tmp_path)
	thumb, export = _caches(library, "gone.avif")
	trash = FakeTrash()
	use_case = TrashGalleryItems(fs, trash)
	# when
	results = use_case.run(library, ["gone.avif"])
	# then
	assert results[0].outcome is TrashOutcome.ALREADY_GONE
	assert trash.trashed == []
	assert not thumb.exists()
	assert not export.exists()


def test_given_unsafe_path_in_list_when_trash_then_nothing_touched(tmp_path) -> None:
	# given
	library, fs = _library(tmp_path)
	ok = _processed(fs, library, "ok.avif")
	trash = FakeTrash()
	use_case = TrashGalleryItems(fs, trash)
	# when
	# then
	with pytest.raises(UnsafeBatchPathError):
		use_case.run(library, ["ok.avif", "../outside.avif"])
	assert trash.trashed == []
	assert Path(ok).is_file()


def test_given_too_many_paths_when_trash_then_rejected_before_any_trash(tmp_path) -> None:
	# given
	library, fs = _library(tmp_path)
	trash = FakeTrash()
	use_case = TrashGalleryItems(fs, trash)
	paths = [f"{i}.avif" for i in range(MAX_GALLERY_BATCH_ITEMS + 1)]
	# when
	# then
	with pytest.raises(BatchTooLargeError):
		use_case.run(library, paths)
	assert trash.trashed == []


def test_given_trash_port_when_use_case_inspected_then_filesystem_delete_is_never_used(tmp_path) -> None:
	# given
	library, fs = _library(tmp_path)
	_processed(fs, library, "a.avif")

	class NoDeleteFs(LocalFileSystem):
		def delete_file(self, path: str) -> None:
			# derived caches may be deleted, user media must never be
			assert "/processed/" not in path.replace("\\", "/"), path
			super().delete_file(path)

	trash = FakeTrash()
	use_case = TrashGalleryItems(NoDeleteFs(), trash)
	# when
	use_case.run(library, ["a.avif"])
	# then
	assert len(trash.trashed) == 1
