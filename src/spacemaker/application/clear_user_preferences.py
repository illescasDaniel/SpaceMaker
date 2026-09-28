from __future__ import annotations

from spacemaker.ports.outbound.user_preferences import UserPreferencesPort


class ClearUserPreferences:
	def __init__(self, preferences: UserPreferencesPort) -> None:
		self._preferences = preferences

	def run(self) -> None:
		self._preferences.clear()
