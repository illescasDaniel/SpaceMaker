import re
from pathlib import Path

from spacemaker.bootstrap.bundled_tools import BundledTool


_REPO = Path(__file__).resolve().parents[2]
_MANIFEST = _REPO / "packaging" / "third-party-manifest.yaml"


def _manifest_ids() -> set[str]:
	text = _MANIFEST.read_text(encoding="utf-8")
	return set(re.findall(r"^\s*-\s*id:\s*(\S+)\s*$", text, re.MULTILINE))


def test_given_manifest_when_compare_to_bundled_tool_enum_then_ids_match():
	# given
	manifest_ids = _manifest_ids()
	enum_ids = {t.value for t in BundledTool}
	# when / then
	assert manifest_ids == enum_ids
