"""Markup guards for the url-field spec (specs/url-field/SPEC.md): no dead ⓘ buttons, URL fields share one shape."""

import re
from pathlib import Path


STATIC = Path(__file__).resolve().parents[2] / "src" / "spacemaker" / "adapters" / "inbound" / "web" / "static"
INDEX = (STATIC / "index.html").read_text(encoding="utf-8")

INFO_BTN_RE = re.compile(r"<button\b[^>]*\bclass=\"[^\"]*\binfo-btn\b[^>]*>", re.S)
ARIA_CONTROLS_RE = re.compile(r'aria-controls="([^"]+)"')
PANEL_ID_RE = re.compile(r'<div\b[^>]*\bclass="[^"]*\binfo-panel\b[^"]*"[^>]*\bid="([^"]+)"')
URL_FIELD_RE = re.compile(r'<div class="url-field"[^>]*>(.*?)</div>', re.S)
URL_INPUT_IDS = (
	"easy-qr-url",
	"receive-qr-url",
	"send-qr-url",
	"transfer-qr-url",
	"wifi-qr-url-copy",
	"wifi-upload-url",
	"gallery-url",
	"gallery-popup-url",
)


def test_given_index_html_when_listing_info_buttons_then_each_controls_an_existing_info_panel():
	# given
	buttons = INFO_BTN_RE.findall(INDEX)
	panel_ids = set(PANEL_ID_RE.findall(INDEX))

	# when
	controlled = [ARIA_CONTROLS_RE.search(button) for button in buttons]

	# then
	assert buttons
	for button, match in zip(buttons, controlled, strict=True):
		assert match, f"info button without aria-controls: {button}"
		assert match.group(1) in panel_ids, f"no .info-panel with id {match.group(1)!r}"


def test_given_index_html_when_listing_info_buttons_then_ids_are_unique():
	# given
	buttons = INFO_BTN_RE.findall(INDEX)

	# when
	ids = [m.group(1) for b in buttons if (m := re.search(r'\bid="([^"]+)"', b))]

	# then
	assert len(ids) == len(set(ids))


def test_given_index_html_when_looking_for_url_inputs_then_each_is_a_readonly_input_inside_a_url_field():
	# given
	fields = URL_FIELD_RE.findall(INDEX)

	# when / then
	for input_id in URL_INPUT_IDS:
		holder = [f for f in fields if f'id="{input_id}"' in f]
		assert holder, f"#{input_id} is not inside a .url-field"
		assert re.search(
			rf'<input\b[^>]*\bid="{input_id}"[^>]*\breadonly\b|<input\b[^>]*\breadonly\b[^>]*\bid="{input_id}"',
			holder[0],
		), f"#{input_id} must be a readonly <input>"
		assert 'class="url-copy"' in holder[0], f"#{input_id} needs a .url-copy button"


def test_given_index_html_when_checking_gallery_urls_then_no_plain_div_field_shows_a_url():
	# given
	html = INDEX

	# when / then
	assert 'class="field" id="gallery-url"' not in html
	assert 'class="field" id="gallery-popup-url"' not in html


def test_given_reduced_motion_when_panel_or_copied_animate_then_they_use_the_zeroed_duration_tokens():
	# given
	theme = (STATIC / "theme.css").read_text(encoding="utf-8")
	components = (STATIC / "shell-components.css").read_text(encoding="utf-8")

	# when
	reduced = theme.split("prefers-reduced-motion: reduce", 1)[1]

	# then
	assert "--dur-fast: 0.001ms" in reduced
	assert "--dur-base: 0.001ms" in reduced
	assert "var(--dur-fast)" in components.split(".url-copy {", 1)[1].split("}", 1)[0]
	assert "animation: panel-fade-in var(--dur-base)" in components
