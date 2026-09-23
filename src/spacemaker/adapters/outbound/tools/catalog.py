from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def catalog_path(repo_root: Path) -> Path:
	return repo_root / "packaging" / "tool-catalog.json"


def load_platform_catalog(*, repo_root: Path, platform_key: str) -> dict[str, dict[str, Any]]:
	path = catalog_path(repo_root)
	if not path.is_file():
		return {}
	data = json.loads(path.read_text(encoding="utf-8"))
	platforms = data.get("platforms", {})
	block = platforms.get(platform_key, {})
	if not isinstance(block, dict):
		return {}
	out: dict[str, dict[str, Any]] = {}
	for key, value in block.items():
		if isinstance(value, dict):
			out[str(key)] = value
	return out
