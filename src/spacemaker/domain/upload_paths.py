from __future__ import annotations

from pathlib import PurePosixPath


def is_safe_upload_relative_path(relative: str) -> bool:
	if not relative or relative.startswith("/") or relative.startswith("\\"):
		return False
	normalized = relative.replace("\\", "/")
	parts = PurePosixPath(normalized).parts
	if ".." in parts:
		return False
	return bool(parts)


def normalize_upload_relative_path(raw: str) -> str | None:
	if not raw:
		return None
	clean = raw.replace("\\", "/").strip().lstrip("/")
	if not is_safe_upload_relative_path(clean):
		return None
	return clean
