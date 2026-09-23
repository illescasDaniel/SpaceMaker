from __future__ import annotations

from spacemaker.domain.library import LibraryFolder
from spacemaker.domain.media import MediaKind, media_kind_for_extension, normalize_extension
from spacemaker.ports.outbound.filesystem import FileSystemPort


def count_image_files_in_library_folder(
	filesystem: FileSystemPort,
	library_root: str,
	folder: LibraryFolder,
) -> int:
	rel_paths = filesystem.list_files_in_library_folder(library_root, folder)
	return sum(1 for rel in rel_paths if media_kind_for_extension(normalize_extension(rel)) is MediaKind.IMAGE)
