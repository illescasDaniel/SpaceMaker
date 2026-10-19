from __future__ import annotations

from enum import StrEnum

from spacemaker.adapters.inbound.web.client_access import is_loopback_client_host


class SpaEntry(StrEnum):
	"""Which HTML shell to serve for a browser navigation."""

	DESKTOP = "desktop"
	MOBILE_GALLERY = "mobile_gallery"
	MOBILE_REMOTE = "mobile_remote"  # the "SpaceMaker is controlled from the computer" notice


def spa_entry_for(*, client_host: str | None, path: str) -> SpaEntry:
	"""Pick the shell from the TCP peer, never the Host header (spec: lan-access)."""
	normalized_path = path if path.startswith("/") else f"/{path}"
	if is_loopback_client_host(client_host):
		return SpaEntry.DESKTOP
	if normalized_path == "/gallery" or normalized_path.startswith("/gallery/"):
		return SpaEntry.MOBILE_GALLERY
	return SpaEntry.MOBILE_REMOTE
