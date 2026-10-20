from __future__ import annotations

import secrets
import threading

from spacemaker.domain.device_stream import DeviceStreamGrant


class DeviceStreamTokens:
	"""Thread-safe in-memory registry of opaque stream tokens, each granting reads of one phone file.

	Tokens are 128-bit random values (``secrets.token_urlsafe(16)``) and live until revoked or the app exits.
	"""

	def __init__(self) -> None:
		self._grants: dict[str, DeviceStreamGrant] = {}
		self._lock = threading.Lock()

	def mint(self, grant: DeviceStreamGrant) -> str:
		"""Register ``grant`` and return its new token."""
		token = secrets.token_urlsafe(16)
		with self._lock:
			self._grants[token] = grant
		return token

	def resolve(self, token: str) -> DeviceStreamGrant | None:
		"""The grant for ``token`` or ``None`` when unknown or revoked."""
		with self._lock:
			return self._grants.get(token)

	def revoke(self, token: str) -> None:
		"""Forget ``token``; unknown tokens are ignored."""
		with self._lock:
			self._grants.pop(token, None)
