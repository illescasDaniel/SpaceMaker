from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
	import sys

	from spacemaker.bootstrap.paths import bundle_resource_root

	bundled = bundle_resource_root()
	if bundled is not None:
		return bundled
	if getattr(sys, "frozen", False):
		meipass = getattr(sys, "_MEIPASS", None)
		if meipass:
			return Path(meipass)
	return Path(__file__).resolve().parents[4]
