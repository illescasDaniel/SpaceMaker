"""Shared formatting helpers for codenav/webnav MCP tool responses."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


def uri_to_path(uri: str) -> Path:
	parsed = urlparse(uri)
	return Path(unquote(parsed.path.lstrip("/") if os.name == "nt" else parsed.path))


def uri_to_relative(uri: str, workspace_root: Path) -> str:
	path = uri_to_path(uri)
	try:
		return str(path.relative_to(workspace_root)).replace("\\", "/")
	except ValueError:
		return str(path)


def snippet(uri: str, start_line: int, end_line: int, *, context: int = 0) -> str:
	path = uri_to_path(uri)
	try:
		lines = path.read_text(encoding="utf-8").splitlines()
	except OSError:
		return ""
	lo = max(0, start_line - context)
	hi = min(len(lines), end_line + 1 + context)
	numbered = [f"{i + 1:>5} | {lines[i]}" for i in range(lo, hi)]
	return "\n".join(numbered)


def _location_range(loc: dict[str, Any]) -> dict[str, Any]:
	"""Prefer LocationLink selection range when present (narrower symbol span)."""
	if "targetSelectionRange" in loc:
		return loc["targetSelectionRange"] or {}
	return loc.get("range") or loc.get("targetRange") or {}


def format_location(loc: dict[str, Any], workspace_root: Path) -> str:
	uri = loc.get("uri") or loc.get("targetUri", "")
	rng = _location_range(loc)
	start = rng.get("start", {})
	end = rng.get("end", {})
	start_line = start.get("line", 0)
	start_col = start.get("character", 0)
	end_line = end.get("line", start_line)
	rel = uri_to_relative(uri, workspace_root)
	header = f"{rel}:{start_line + 1}:{start_col + 1}"
	body = snippet(uri, start_line, end_line, context=2)
	return f"{header}\n{body}" if body else header
