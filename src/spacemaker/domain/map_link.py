from __future__ import annotations

import math
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit


MAPS_SEARCH_PREFIX = "https://www.google.com/maps/search/?api=1&query="
_NUMBER = r"-?\d{1,3}(?:\.\d{1,10})?"
_QUERY = re.compile(rf"^({_NUMBER}),({_NUMBER})$")


@dataclass(frozen=True, slots=True)
class MapPoint:
	"""A validated WGS84 coordinate: latitude in [-90, 90], longitude in [-180, 180]."""

	latitude: float
	longitude: float

	def __post_init__(self) -> None:
		if not (math.isfinite(self.latitude) and -90.0 <= self.latitude <= 90.0):
			raise ValueError("latitude out of range")
		if not (math.isfinite(self.longitude) and -180.0 <= self.longitude <= 180.0):
			raise ValueError("longitude out of range")


def maps_url(point: MapPoint) -> str:
	"""Google Maps search URL built only from validated numbers (6 dp max, trailing zeros trimmed)."""
	return f"{MAPS_SEARCH_PREFIX}{_fmt(point.latitude)},{_fmt(point.longitude)}"


def parse_maps_url(url: str) -> MapPoint | None:
	"""Return the point when ``url`` is exactly a Maps search URL for two in-range decimals, else None."""
	try:
		parts = urlsplit(url)
		params = parse_qs(parts.query, keep_blank_values=True, strict_parsing=True)
	except ValueError:
		return None
	if parts.scheme != "https" or parts.netloc != "www.google.com" or parts.path != "/maps/search/":
		return None
	if parts.fragment or set(params) != {"api", "query"}:
		return None
	if params["api"] != ["1"] or len(params["query"]) != 1:
		return None
	match = _QUERY.match(params["query"][0])
	if match is None:
		return None
	try:
		return MapPoint(float(match.group(1)), float(match.group(2)))
	except ValueError:
		return None


def _fmt(value: float) -> str:
	text = f"{value:.6f}".rstrip("0").rstrip(".")
	return "0" if text in ("", "-0") else text
