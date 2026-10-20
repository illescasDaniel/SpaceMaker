"""CSS guards for the narrow-window lightbox scenario (specs/device-file-picker/SPEC.md)."""

import re
from pathlib import Path


STATIC = Path(__file__).resolve().parents[2] / "src" / "spacemaker" / "adapters" / "inbound" / "web" / "static"
SHELL_LAYOUT = (STATIC / "shell-layout.css").read_text(encoding="utf-8")
NARROW_BLOCK_RE = re.compile(r"@media \(max-width: 520px\) \{(.*?)\n\t\t\}", re.S)


def _narrow_blocks() -> list[str]:
	return NARROW_BLOCK_RE.findall(SHELL_LAYOUT)


def _rule(block: str, selector: str) -> str:
	match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", block)
	assert match, f"{selector} missing in narrow block"
	return match.group(1)


def test_given_narrow_window_when_picker_list_then_thumbnail_shrinks_to_36px() -> None:
	# given
	blocks = [b for b in _narrow_blocks() if ".dp-list" in b]
	# when
	rule = _rule(blocks[0], ".dp-list")
	# then
	assert "--dp-thumb: 36px" in rule


def test_given_narrow_window_when_lightbox_then_panel_is_full_screen() -> None:
	# given
	block = next(b for b in _narrow_blocks() if ".dp-lb-panel" in b)
	# when
	rule = _rule(block, ".dp-lb-panel")
	# then
	assert "width: 100%" in rule
	assert "height: 100%" in rule


def test_given_narrow_window_when_lightbox_then_nav_buttons_sit_below_the_photo() -> None:
	# given
	block = next(b for b in _narrow_blocks() if ".dp-lb-panel" in b)
	# when
	photo = _rule(block, ".dp-lb-photo")
	prev = _rule(block, ".dp-lb-prev")
	next_ = _rule(block, ".dp-lb-next")
	# then
	assert "grid-area: 1 / 1 / 2 / 3" in photo
	assert "grid-area: 2 / 1" in prev
	assert "grid-area: 2 / 2" in next_
