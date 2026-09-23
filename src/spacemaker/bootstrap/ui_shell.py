"""Desktop / phone web UI shell version (bump when static assets change materially)."""

UI_SHELL_VERSION = "2026.09.home-modules"

CONTENT_SECURITY_POLICY = (
	"default-src 'self'; "
	"script-src 'self' 'unsafe-inline'; "
	"style-src 'self' 'unsafe-inline'; "
	"img-src 'self' data: blob:; "
	"media-src 'self'; "
	"connect-src 'self' ws: wss:; "
	"base-uri 'self'; "
	"frame-ancestors 'none'"
)

NO_CACHE_HEADERS = {"Cache-Control": "no-store, must-revalidate"}


def webengine_profile_slug() -> str:
	return UI_SHELL_VERSION.replace(".", "-")
