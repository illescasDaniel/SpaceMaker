from __future__ import annotations

UI_SHELL_VERSION = "2026.09.usb-file-transfer"

# Cache-busting query for shell assets. Bump UI_SHELL_VERSION when shipping static UI changes.
def shell_asset_query() -> str:
	return f"v={UI_SHELL_VERSION}"


def shell_etag_token() -> str:
	return UI_SHELL_VERSION.replace(".", "-")
