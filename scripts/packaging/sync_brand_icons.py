#!/usr/bin/env python3
"""Regenerate app icon + favicon PNGs from packaging/assets/spacemaker-icon-source.png.

On macOS, also builds packaging/assets/spacemaker.icns via iconutil (for SpaceMaker.app).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image


_REPO = Path(__file__).resolve().parents[2]
_ASSETS = _REPO / "packaging" / "assets"
_STATIC = _REPO / "src" / "spacemaker" / "adapters" / "inbound" / "web" / "static"
_SOURCE = _ASSETS / "spacemaker-icon-source.png"
_ICNS = _ASSETS / "spacemaker.icns"

# Apple iconset filenames → pixel size (1x and 2x where required).
_ICONSET_SIZES: tuple[tuple[str, int], ...] = (
	("icon_16x16.png", 16),
	("diana.k@example.org", 32),
	("icon_32x32.png", 32),
	("ivan.p@example.net", 64),
	("icon_128x128.png", 128),
	("wendy.h@example.net", 256),
	("icon_256x256.png", 256),
	("wendy.h@example.net", 512),
	("icon_512x512.png", 512),
	("walt.e@example.net", 1024),
)


def _save_resize(master: Image.Image, size: int, path: Path) -> None:
	img = master.resize((size, size), Image.Resampling.LANCZOS)
	path.parent.mkdir(parents=True, exist_ok=True)
	img.save(path, format="PNG", optimize=True)


def _write_icns(master: Image.Image) -> None:
	"""Build spacemaker.icns with iconutil (macOS only)."""
	if sys.platform != "darwin":
		return
	if shutil.which("iconutil") is None:
		print("warning: iconutil not found; skipping .icns", file=sys.stderr)
		return
	with tempfile.TemporaryDirectory(prefix="spacemaker-iconset-") as tmp:
		iconset = Path(tmp) / "SpaceMaker.iconset"
		iconset.mkdir()
		for name, size in _ICONSET_SIZES:
			_save_resize(master, size, iconset / name)
		subprocess.run(
			["iconutil", "-c", "icns", str(iconset), "-o", str(_ICNS)],
			check=True,
		)
	print(f"Wrote {_ICNS.relative_to(_REPO)}")


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
	_write_icns(master)
	print(f"Synced brand icons from {_SOURCE.name}")
	return 0


if __name__ == "__main__":
	sys.exit(main())
