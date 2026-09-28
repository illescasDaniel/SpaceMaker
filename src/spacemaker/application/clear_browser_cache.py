from __future__ import annotations

from spacemaker.ports.outbound.filesystem import FileSystemPort


class ClearBrowserCache:
	"""Wipe the desktop webview's on-disk HTTP cache (cookies, local storage, cached responses).

	Self-regenerating: the webview recreates an empty profile directory on next launch or
	request. Never touches library media, the gallery index, or disk-backed preferences.
	"""

	def __init__(self, filesystem: FileSystemPort) -> None:
		self._filesystem = filesystem

	def run(self, storage_path: str) -> None:
		if not storage_path:
			raise ValueError("storage_path required")
		self._filesystem.delete_directory(storage_path)
