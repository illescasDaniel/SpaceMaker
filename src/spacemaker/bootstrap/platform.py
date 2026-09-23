from __future__ import annotations

import platform
import sys


def platform_catalog_key() -> str:
	machine = platform.machine().lower()
	if machine in {"x86_64", "amd64"}:
		arch = "x86_64"
	elif machine in {"aarch64", "arm64"}:
		arch = "aarch64"
	else:
		arch = machine.replace("-", "_")
	if sys.platform == "win32":
		return f"win-{arch}"
	if sys.platform == "darwin":
		return f"macos-{arch}"
	return f"linux-{arch}"
