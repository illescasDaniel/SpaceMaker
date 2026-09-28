from __future__ import annotations

from pathlib import Path

from spacemaker.domain.gallery_export import ExportFormat
from spacemaker.domain.library_paths import CONVERT_STAGING_DIR_NAME, EXPORTS_DIR_NAME, THUMBNAILS_DIR_NAME


def _normalize_relative(relative_path: str) -> str:
	return relative_path.replace("\\", "/").lstrip("/")


def _append_cache_extension(relative_path: str, extension: str) -> str:
	"""Injective cache key: keep the full relative path, append the cache extension."""
	normalized = _normalize_relative(relative_path)
	ext = extension if extension.startswith(".") else f".{extension}"
	return f"{normalized}{ext}"


def thumbnail_path(library_root: str, relative_path: str) -> str:
	"""Absolute path for a gallery thumbnail cache file (append .jpg to relative path)."""
	rel = _append_cache_extension(relative_path, ".jpg")
	return str(Path(library_root) / THUMBNAILS_DIR_NAME / Path(rel))


def convert_staging_root(library_root: str) -> str:
	"""Absolute path for the convert-staging directory (holds in-progress encode output)."""
	return str(Path(library_root) / CONVERT_STAGING_DIR_NAME)


def convert_staging_path(library_root: str, relative_path: str) -> str:
	"""Absolute path for an in-progress convert output, mirroring its eventual processed/ path."""
	rel = _normalize_relative(relative_path)
	return str(Path(library_root) / CONVERT_STAGING_DIR_NAME / Path(rel))


def export_cache_path(library_root: str, relative_path: str, export_format: ExportFormat) -> str:
	"""Absolute path for a friendly-export cache file (append .jpg or .mp4 to relative path)."""
	ext = ".jpg" if export_format is ExportFormat.JPEG else ".mp4"
	rel = _append_cache_extension(relative_path, ext)
	return str(Path(library_root) / EXPORTS_DIR_NAME / Path(rel))


def export_cache_paths_for_relative(library_root: str, relative_path: str) -> tuple[str, ...]:
	"""Both possible friendly-export cache paths for a gallery relative path."""
	return tuple(export_cache_path(library_root, relative_path, fmt) for fmt in ExportFormat)


def is_legacy_hash_export_filename(name: str) -> bool:
	"""True for pre-path-mirror flat hashes: 20 hex chars + .jpg|.mp4."""
	stem, sep, ext = name.partition(".")
	if sep != "." or ext not in {"jpg", "mp4"}:
		return False
	if len(stem) != 20:
		return False
	return all(c in "0123456789abcdef" for c in stem)
