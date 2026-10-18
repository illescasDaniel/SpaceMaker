from __future__ import annotations

from pathlib import Path

import webview

from spacemaker.adapters.inbound.desktop_download import DownloadRegistry, is_allowed_download_url
from spacemaker.adapters.outbound.host.webbrowser_opener import WebbrowserUrlOpener
from spacemaker.application.file_share_manifest import count_shareable_files_in_root
from spacemaker.application.open_map_location import OpenMapLocation
from spacemaker.bootstrap.paths import default_library_root, normalize_library_root, pictures_directory


class DesktopApi:
	def __init__(self) -> None:
		self._downloads = DownloadRegistry()

	def save_download(self, url: str, suggested_name: str) -> str:
		"""Ask where to save, then stream ``url`` there. Returns a download id, or "" when cancelled or refused."""
		windows = webview.windows
		if not windows or not is_allowed_download_url(url):
			return ""
		result = windows[0].create_file_dialog(
			webview.FileDialog.SAVE,
			directory=str(pictures_directory()),
			save_filename=Path(suggested_name).name or "spacemaker-media.zip",
		)
		if not result:
			return ""
		destination = result[0] if isinstance(result, (list, tuple)) else result
		return self._downloads.start(url, str(destination))

	def download_progress(self, download_id: str) -> dict[str, object]:
		return self._downloads.progress(download_id)

	def open_external_url(self, url: str) -> bool:
		"""Open a validated Google Maps point in the system browser (anything else is refused)."""
		return OpenMapLocation(WebbrowserUrlOpener()).run(url)

	def choose_files(self, current: str = "") -> list[str]:
		windows = webview.windows
		if not windows:
			return []
		directory = str(Path((current or default_library_root()).strip()).parent)
		if not Path(directory).is_dir():
			directory = str(pictures_directory())
		result = windows[0].create_file_dialog(
			webview.FileDialog.OPEN,
			directory=directory,
			allow_multiple=True,
		)
		if not result:
			return []
		if isinstance(result, (list, tuple)):
			return [str(item) for item in result]
		return [str(result)]

	def choose_share_folder(self, current: str = "") -> str:
		windows = webview.windows
		if not windows:
			return ""
		start = (current or default_library_root()).strip()
		directory = str(Path(start).parent) if start else str(pictures_directory())
		if not Path(directory).is_dir():
			directory = str(pictures_directory())
		result = windows[0].create_file_dialog(webview.FileDialog.FOLDER, directory=directory)
		if result:
			first = result[0] if isinstance(result, (list, tuple)) else result
			return normalize_library_root(str(first))
		return ""

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

	def choose_device_files(self, mount_root: str = "") -> list[str]:
		"""Native multi-file picker starting at the phone mount root."""
		windows = webview.windows
		if not windows:
			return []
		directory = (mount_root or "").strip()
		if not directory or not Path(directory).is_dir():
			return []
		result = windows[0].create_file_dialog(
			webview.FileDialog.OPEN,
			directory=directory,
			allow_multiple=True,
		)
		if not result:
			return []
		if isinstance(result, (list, tuple)):
			return [str(item) for item in result]
		return [str(result)]

	def choose_device_folder(self, mount_root: str = "") -> str:
		"""Native folder picker starting at the phone mount root."""
		windows = webview.windows
		if not windows:
			return ""
		directory = (mount_root or "").strip()
		if not directory or not Path(directory).is_dir():
			return ""
		result = windows[0].create_file_dialog(webview.FileDialog.FOLDER, directory=directory)
		if not result:
			return ""
		first = result[0] if isinstance(result, (list, tuple)) else result
		return str(first)

	def share_folder_file_count(self, folder: str) -> int:
		text = (folder or "").strip()
		if not text:
			return 0
		return count_shareable_files_in_root(Path(text))
