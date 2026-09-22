from __future__ import annotations

from pathlib import Path

import webview

from spacemaker.bootstrap.paths import default_library_root, normalize_library_root, pictures_directory


class DesktopApi:
	def choose_library_folder(self, current: str = "") -> str:
		windows = webview.windows
		if not windows:
			return current
		start = (current or default_library_root()).strip()
		directory = str(Path(start).parent) if start else str(pictures_directory())
		if not Path(directory).is_dir():
			directory = str(pictures_directory())
		result = windows[0].create_file_dialog(webview.FileDialog.FOLDER, directory=directory)
		if result:
			first = result[0] if isinstance(result, (list, tuple)) else result
			return normalize_library_root(str(first))
		return current
