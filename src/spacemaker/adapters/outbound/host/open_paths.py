from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def open_file_with_default_app(path: str) -> None:
	target = Path(path).resolve()
	if not target.is_file():
		raise FileNotFoundError(str(target))
	if sys.platform == "darwin":
		subprocess.run(["open", str(target)], check=True)
	elif sys.platform == "win32":
		os.startfile(str(target))  # noqa: S606
	else:
		subprocess.run(["xdg-open", str(target)], check=True)


def reveal_in_file_manager(path: str) -> None:
	target = Path(path).resolve()
	if not target.exists():
		raise FileNotFoundError(str(target))
	if sys.platform == "darwin":
		subprocess.run(["open", "-R", str(target)], check=True)
	elif sys.platform == "win32":
		subprocess.run(["explorer", "/select,", str(target)], check=True)
	else:
		open_path = str(target) if target.is_dir() else str(target.parent)
		subprocess.run(["xdg-open", open_path], check=True)
