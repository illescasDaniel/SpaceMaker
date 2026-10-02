from __future__ import annotations

import webbrowser


class WebbrowserUrlOpener:
	"""Open URLs in the user's default system browser."""

	def open(self, url: str) -> bool:
		try:
			return bool(webbrowser.open(url))
		except webbrowser.Error:
			return False
