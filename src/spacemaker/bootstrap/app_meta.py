"""Release identity (mirrors [project] in pyproject.toml)."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

APP_AUTHOR = "Daniel Illescas Romero"
APP_CONTACT_EMAIL = "contact@daniel-ir.eu"
_FALLBACK_VERSION = "1.0.0"


def app_version() -> str:
	try:
		return version("spacemaker")
	except PackageNotFoundError:
		return _FALLBACK_VERSION


def app_release_info() -> dict[str, str]:
	return {
		"app_version": app_version(),
		"app_author": APP_AUTHOR,
		"app_contact": APP_CONTACT_EMAIL,
	}
