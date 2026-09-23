#!/usr/bin/env python3
"""Regenerate app icon + favicon PNGs from packaging/assets/spacemaker-icon-source.png."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


_REPO = Path(__file__).resolve().parents[2]
_ASSETS = _REPO / "packaging" / "assets"
_STATIC = _REPO / "src" / "spacemaker" / "adapters" / "inbound" / "web" / "static"
_SOURCE = _ASSETS / "spacemaker-icon-source.png"


def _save_resize(master: Image.Image, size: int, path: Path) -> None:
	img = master.resize((size, size), Image.Resampling.LANCZOS)
	path.parent.mkdir(parents=True, exist_ok=True)
	img.save(path, format="PNG", optimize=True)


def main() -> int:
	if not _SOURCE.is_file():
		print(f"error: missing master icon {_SOURCE}", file=sys.stderr)
		return 1
	master = Image.open(_SOURCE).convert("RGBA")
	_save_resize(master, 1024, _SOURCE)
	_save_resize(master, 1024, _ASSETS / "spacemaker-icon.png")
	for size in (32,):
		_save_resize(master, size, _ASSETS / f"favicon-{size}.png")
	_save_resize(master, 32, _STATIC / "favicon.png")
	_save_resize(master, 180, _STATIC / "apple-touch-icon.png")
	print(f"Synced brand icons from {_SOURCE.name}")
	return 0


if __name__ == "__main__":
	sys.exit(main())
