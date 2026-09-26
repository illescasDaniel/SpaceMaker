"""Desktop / phone web UI shell version (bump when static assets change materially)."""

UI_SHELL_VERSION = "2026.09.usb-file-transfer"

_CSP_COMMON = (
	"default-src 'self'; "
	"style-src 'self' 'unsafe-inline'; "
	"font-src 'self'; "
	"img-src 'self' data: blob:; "
	"media-src 'self'; "
	"connect-src 'self' ws: wss:; "
	"base-uri 'self'; "
	"frame-ancestors 'none'; "
)

# LAN phone pages (upload/gallery QR): no eval.
CONTENT_SECURITY_POLICY = f"{_CSP_COMMON}script-src 'self' 'unsafe-inline'"

# Desktop pywebview (loopback): js_api bridge uses new Function() — requires unsafe-eval.
CONTENT_SECURITY_POLICY_DESKTOP = f"{_CSP_COMMON}script-src 'self' 'unsafe-inline' 'unsafe-eval'"

NO_CACHE_HEADERS = {"Cache-Control": "no-store, must-revalidate"}


def webengine_profile_slug() -> str:
	return UI_SHELL_VERSION.replace(".", "-")
