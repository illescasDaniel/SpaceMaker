from __future__ import annotations

from enum import StrEnum
from ipaddress import ip_address


class SpaEntry(StrEnum):
	"""Which HTML shell to serve for a browser navigation."""

	DESKTOP = "desktop"
	MOBILE_GALLERY = "mobile_gallery"
	MOBILE_REMOTE = "mobile_remote"


def normalize_host(host_header: str) -> str:
	raw = (host_header or "").strip().lower()
	if not raw:
		return ""
	if raw.startswith("["):
		end = raw.find("]")
		if end != -1:
			return raw[1:end]
	return raw.split(":")[0]


def is_loopback_host(host: str) -> bool:
	if not host:
		return True
	if host in {"localhost", "127.0.0.1", "::1"}:
		return True
	try:
		return ip_address(host).is_loopback
	except ValueError:
		return False


def is_private_lan_host(host: str) -> bool:
	try:
		addr = ip_address(host)
	except ValueError:
		return False
	return addr.is_private and not addr.is_loopback


def spa_entry_for(*, host: str, path: str) -> SpaEntry:
	normalized_path = path if path.startswith("/") else f"/{path}"
	if is_loopback_host(host) or not is_private_lan_host(host):
		return SpaEntry.DESKTOP
	if normalized_path == "/gallery" or normalized_path.startswith("/gallery/"):
		return SpaEntry.MOBILE_GALLERY
	return SpaEntry.MOBILE_REMOTE
