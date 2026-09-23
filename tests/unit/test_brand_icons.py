from pathlib import Path

from PIL import Image


_REPO = Path(__file__).resolve().parents[2]
_ASSETS = _REPO / "packaging" / "assets"
_STATIC = _REPO / "src" / "spacemaker" / "adapters" / "inbound" / "web" / "static"


def test_given_repo_when_check_brand_icon_source_then_master_file_exists():
	assert (_ASSETS / "spacemaker-icon-source.png").is_file()


def test_given_repo_when_check_brand_icons_then_pngs_exist_with_expected_sizes():
	# given
	expected = {
		_ASSETS / "spacemaker-icon.png": 1024,
		_ASSETS / "favicon-32.png": 32,
		_STATIC / "favicon.png": 32,
		_STATIC / "apple-touch-icon.png": 180,
	}
	# when / then
	for path, size in expected.items():
		assert path.is_file(), f"missing {path}"
		with Image.open(path) as img:
			assert img.format == "PNG"
			assert img.size == (size, size)
