"""Desktop / phone web UI shell version (bump when static assets change materially)."""

UI_SHELL_VERSION = "2026.09.home-modules"

NO_CACHE_HEADERS = {"Cache-Control": "no-store, must-revalidate"}


def webengine_profile_slug() -> str:
	return UI_SHELL_VERSION.replace(".", "-")
