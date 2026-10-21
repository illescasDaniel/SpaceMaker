from __future__ import annotations

from spacemaker.domain.device_browse import normalize_browse_path
from spacemaker.domain.device_view import EMPTY_VIEW_MEMORY, DeviceViewHints, DeviceViewSetting, view_hints
from spacemaker.ports.outbound.user_preferences import UserPreferencesPort


class DeviceFolderViews:
	"""Phone picker layout per folder: hints for the client and the user's per-folder choice.

	Neither method touches the device: hints need no listing, so the list route can report them even when the
	listing fails.
	"""

	def __init__(self, preferences: UserPreferencesPort | None = None) -> None:
		self._preferences = preferences

	def hints(self, path: str) -> DeviceViewHints:
		"""``view_hints`` for the normalized ``path`` (stored choice empty without ``preferences``).

		Raises ``DeviceBrowseError(INVALID_PATH)`` like ``normalize_browse_path``.
		"""
		relative = normalize_browse_path(path)
		memory = self._preferences.get_device_picker_views() if self._preferences is not None else EMPTY_VIEW_MEMORY
		return view_hints(relative, memory)

	def choose(self, path: str, setting: DeviceViewSetting) -> None:
		"""Store (``LIST`` / ``GRID``) or forget (``AUTO``) the choice for the normalized ``path``.

		Raises ``DeviceBrowseError(INVALID_PATH)`` before any write; a no-op without ``preferences``.
		"""
		relative = normalize_browse_path(path)
		if self._preferences is not None:
			self._preferences.set_device_picker_view(relative, setting)
