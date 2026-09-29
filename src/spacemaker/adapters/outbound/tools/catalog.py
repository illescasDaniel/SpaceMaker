from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, cast


class CatalogEntry(TypedDict, total=False):
	"""One tool row from packaging/tool-catalog.json for a platform key."""

	strategy: str
	url: str
	files: dict[str, str]
	companion_of: str
	prefix: str
	launcher: str
	version: str
	sha256: str


def catalog_path(repo_root: Path) -> Path:
	return repo_root / "packaging" / "tool-catalog.json"


def load_platform_catalog(*, repo_root: Path, platform_key: str) -> dict[str, CatalogEntry]:
	path = catalog_path(repo_root)
	if not path.is_file():
		return {}
	data = json.loads(path.read_text(encoding="utf-8"))
	platforms = data.get("platforms", {})
	block = platforms.get(platform_key, {})
	if not isinstance(block, dict):
		return {}
	out: dict[str, CatalogEntry] = {}
	for key, value in block.items():
		if isinstance(value, dict):
			out[str(key)] = cast(CatalogEntry, value)
	return out
