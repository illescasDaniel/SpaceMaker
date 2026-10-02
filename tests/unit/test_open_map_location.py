import pytest

from spacemaker.application.open_map_location import OpenMapLocation
from spacemaker.domain.map_link import MapPoint, maps_url, parse_maps_url

VALID = "https://www.google.com/maps/search/?api=1&query=52.52,13.405"


class RecordingOpener:
	def __init__(self, result: bool = True) -> None:
		self.opened: list[str] = []
		self._result = result

	def open(self, url: str) -> bool:
		self.opened.append(url)
		return self._result


def test_given_point_when_maps_url_then_decimal_query_with_trimmed_zeros():
	# given
	point = MapPoint(52.52, 13.405)
	# when
	url = maps_url(point)
	# then
	assert url == VALID


def test_given_negative_point_when_maps_url_then_signs_kept():
	# given
	point = MapPoint(-33.8688, -70.0)
	# when
	url = maps_url(point)
	# then
	assert url.endswith("query=-33.8688,-70")


@pytest.mark.parametrize(
	"lat,lon", [(90.1, 0.0), (-91.0, 0.0), (0.0, 180.5), (0.0, -181.0), (float("nan"), 0.0), (0.0, float("inf"))]
)
def test_given_out_of_range_or_non_finite_when_map_point_then_value_error(lat: float, lon: float):
	# given
	# when / then
	with pytest.raises(ValueError):
		MapPoint(lat, lon)


def test_given_valid_maps_url_when_parse_then_point_returned():
	# given
	url = VALID
	# when
	point = parse_maps_url(url)
	# then
	assert point == MapPoint(52.52, 13.405)


@pytest.mark.parametrize(
	"url",
	[
		"http://www.google.com/maps/search/?api=1&query=52.52,13.405",
		"https://evil.example/maps/search/?api=1&query=52.52,13.405",
		"https://www.google.com.evil.example/maps/search/?api=1&query=52.52,13.405",
		"https://www.google.com/other/?api=1&query=52.52,13.405",
		"https://www.google.com/maps/search/?api=1&query=95,13",
		"https://www.google.com/maps/search/?api=1&query=52.52",
		"https://www.google.com/maps/search/?api=1&query=a,b",
		"https://www.google.com/maps/search/?api=1&query=1,2&query=3,4",
		"https://www.google.com/maps/search/?api=1&query=1,2&extra=x",
		"https://user@www.google.com/maps/search/?api=1&query=1,2",
		"https://www.google.com/maps/search/?api=1&query=1,2#frag",
		"file:///etc/passwd",
		"javascript:alert(1)",
		"",
	],
)
def test_given_non_maps_or_malformed_url_when_parse_then_none(url: str):
	# given
	# when
	point = parse_maps_url(url)
	# then
	assert point is None


def test_given_valid_url_when_open_then_opener_receives_rebuilt_url():
	# given
	opener = RecordingOpener()
	# when
	opened = OpenMapLocation(opener).run(VALID)
	# then
	assert opened is True
	assert opener.opened == [VALID]


def test_given_refused_url_when_open_then_opener_never_called():
	# given
	opener = RecordingOpener()
	# when
	opened = OpenMapLocation(opener).run("https://evil.example/maps/search/?api=1&query=1,2")
	# then
	assert opened is False
	assert opener.opened == []


def test_given_browser_launch_fails_when_open_then_false():
	# given
	opener = RecordingOpener(result=False)
	# when
	opened = OpenMapLocation(opener).run(VALID)
	# then
	assert opened is False


def test_given_desktop_bridge_when_valid_url_then_webbrowser_opens_it(monkeypatch: pytest.MonkeyPatch):
	# given
	opened: list[str] = []
	monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url) or True)
	from spacemaker.adapters.inbound.desktop_api import DesktopApi

	# when
	result = DesktopApi().open_external_url(VALID)
	refused = DesktopApi().open_external_url("https://evil.example/")
	# then
	assert result is True
	assert refused is False
	assert opened == [VALID]
