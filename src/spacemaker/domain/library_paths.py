from __future__ import annotations

from pathlib import PurePosixPath


# Directory names under library buckets that must not be converted or counted.
SKIPPED_LIBRARY_DIR_NAMES: frozenset[str] = frozenset({".thumbnails", ".exports", ".convert-staging"})

THUMBNAILS_DIR_NAME = ".thumbnails"
EXPORTS_DIR_NAME = ".exports"
CONVERT_STAGING_DIR_NAME = ".convert-staging"
# Inside EXPORTS_DIR_NAME: one folder per gallery batch-convert job holding its zip (see specs/gallery-batch).
BATCH_EXPORTS_DIR_NAME = ".batch"


def skip_library_relative_path(relative: str) -> bool:
	normalized = relative.replace("\\", "/")
	return any(part in SKIPPED_LIBRARY_DIR_NAMES for part in PurePosixPath(normalized).parts)


def skip_media_path(path: str) -> bool:
	"""True for device or library paths under skipped folders (e.g. .thumbnails)."""
	text = path.replace("\\", "/").strip("/")
	if not text:
		return False
	return skip_library_relative_path(text)
