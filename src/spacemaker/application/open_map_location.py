from __future__ import annotations

from spacemaker.domain.map_link import maps_url, parse_maps_url
from spacemaker.ports.outbound.external_url_opener import ExternalUrlOpenerPort


class OpenMapLocation:
	"""Open a Google Maps point in the system browser; refuses any URL that is not a validated Maps search.

	The URL arrives from the web page (untrusted), so it is re-parsed and rebuilt from the two
	validated numbers before the opener sees it. See ``specs/gallery-open-in-maps/SPEC.md``.
	"""

	def __init__(self, opener: ExternalUrlOpenerPort) -> None:
		self._opener = opener

	def run(self, url: str) -> bool:
		point = parse_maps_url(url)
		if point is None:
			return False
		return self._opener.open(maps_url(point))
