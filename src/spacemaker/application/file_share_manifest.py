from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SharedFileEntry:
	entry_id: str
	display_name: str
	absolute_path: str


def expand_share_selection(paths: list[str]) -> list[tuple[str, str]]:
	"""Return (display_name, absolute_path) for each file to share."""
	seen: set[str] = set()
	out: list[tuple[str, str]] = []
	for raw in paths:
		text = raw.strip()
		if not text:
			continue
		path = Path(text).expanduser().resolve()
		if not path.exists():
			continue
		if path.is_file():
			key = str(path)
			if key in seen:
				continue
			seen.add(key)
			out.append((path.name, key))
			continue
		if path.is_dir():
			for child in sorted(path.rglob("*")):
				if not child.is_file():
					continue
				key = str(child)
				if key in seen:
					continue
				seen.add(key)
				try:
					display = str(child.relative_to(path))
				except ValueError:
					display = child.name
				out.append((display.replace("\\", "/"), key))
	return out


def is_path_under_roots(candidate: Path, roots: list[Path]) -> bool:
	text = str(candidate.resolve())
	for root in roots:
		root_text = str(root.resolve())
		if text == root_text or text.startswith(root_text + "/") or text.startswith(root_text + "\\"):
			return True
	return False
