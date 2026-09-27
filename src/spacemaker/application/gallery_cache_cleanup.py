from __future__ import annotations

from pathlib import Path

from spacemaker.domain.gallery_cache_paths import (
	export_cache_paths_for_relative,
	is_legacy_hash_export_filename,
	thumbnail_path,
)
from spacemaker.domain.library_paths import EXPORTS_DIR_NAME
from spacemaker.ports.outbound.filesystem import FileSystemPort


def _delete_if_present(filesystem: FileSystemPort, path: str) -> None:
	if filesystem.exists(path):
		filesystem.delete_file(path)


def delete_gallery_derived_caches(filesystem: FileSystemPort, library_root: str, relative_path: str) -> None:
	"""Remove thumbnail and friendly-export caches for a gallery relative path."""
	_delete_if_present(filesystem, thumbnail_path(library_root, relative_path))
	delete_gallery_export_caches(filesystem, library_root, relative_path)


def delete_gallery_export_caches(filesystem: FileSystemPort, library_root: str, relative_path: str) -> None:
	"""Remove friendly-export caches only (e.g. after source mtime/size change)."""
	for export_path in export_cache_paths_for_relative(library_root, relative_path):
		_delete_if_present(filesystem, export_path)


def sweep_legacy_hash_export_caches(filesystem: FileSystemPort, library_root: str) -> None:
	"""Delete flat hash-named leftovers under .exports/ from the pre-path-mirror layout."""
	exports_dir = str(Path(library_root) / EXPORTS_DIR_NAME)
	for relative in filesystem.list_files_recursive(exports_dir):
		# Legacy layout was flat; path-mirrored caches live under subdirs or include a source suffix.
		if "/" in relative or "\\" in relative:
			continue
		if is_legacy_hash_export_filename(relative):
			_delete_if_present(filesystem, str(Path(exports_dir) / relative))
