from __future__ import annotations

import os
import shutil
from pathlib import Path

from spacemaker.domain.library import LIBRARY_FOLDERS, LibraryFolder
from spacemaker.domain.library_paths import SKIPPED_LIBRARY_DIR_NAMES, skip_library_relative_path


class LocalFileSystem:
	def ensure_library_folders(self, library_root: str) -> None:
		root = Path(library_root)
		root.mkdir(parents=True, exist_ok=True)
		for folder in LIBRARY_FOLDERS:
			(root / folder.value).mkdir(parents=True, exist_ok=True)

	def file_size(self, path: str) -> int:
		return Path(path).stat().st_size

	def exists(self, path: str) -> bool:
		return Path(path).is_file()

	def move_file(self, source: str, destination: str) -> None:
		self.ensure_parent_directory(destination)
		shutil.move(source, destination)

	def ensure_parent_directory(self, file_path: str) -> None:
		Path(file_path).parent.mkdir(parents=True, exist_ok=True)

	def delete_file(self, path: str) -> None:
		Path(path).unlink(missing_ok=True)

	def list_files_recursive(self, folder: str) -> list[str]:
		base = Path(folder)
		if not base.is_dir():
			return []
		out: list[str] = []
		for dirpath, dirnames, filenames in os.walk(base):
			dirnames[:] = [name for name in dirnames if name not in SKIPPED_LIBRARY_DIR_NAMES]
			for name in filenames:
				full = Path(dirpath) / name
				rel = str(full.relative_to(base)).replace("\\", "/")
				if skip_library_relative_path(rel):
					continue
				out.append(rel)
		return sorted(out)

	def list_files_in_library_folder(self, library_root: str, folder: LibraryFolder) -> list[str]:
		prefix = Path(self.library_path(library_root, folder, ""))
		if not prefix.is_dir():
			return []
		out: list[str] = []
		for path in prefix.rglob("*"):
			if not path.is_file():
				continue
			rel = str(path.relative_to(prefix)).replace("\\", "/")
			if skip_library_relative_path(rel):
				continue
			out.append(rel)
		return sorted(out)

	def count_files_in_folder(self, library_root: str, folder: LibraryFolder) -> int:
		return len(self.list_files_in_library_folder(library_root, folder))

	def library_path(self, library_root: str, folder: LibraryFolder, relative: str) -> str:
		base = Path(library_root) / folder.value
		if not relative:
			return str(base)
		return str(base / relative)
