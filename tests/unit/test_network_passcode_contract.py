from __future__ import annotations

from pathlib import Path

import pytest

from spacemaker.adapters.inbound.web.media_paths import _STATIC
from spacemaker.adapters.outbound.preferences.json_store import JsonUserPreferences
from spacemaker.adapters.outbound.preferences.passcode_store import JsonPasscodeStore
from spacemaker.bootstrap.paths import network_passcode_path, user_preferences_path
from spacemaker.domain.network_passcode import PasscodeRecord


PHONE_PAGES = [
	"upload.html",
	"receive.html",
	"share.html",
	"transfer.html",
	"gallery_mobile.html",
	"mobile_remote.html",
]


def test_given_unlock_page_when_read_then_token_comes_from_fragment_and_goes_in_post_body() -> None:
	# given
	html = (_STATIC / "unlock.html").read_text(encoding="utf-8")
	script = (_STATIC / "js" / "unlock.js").read_text(encoding="utf-8")
	# when / then
	assert 'src="/static/js/unlock.js"' in html
	assert 'href="/static/unlock.css"' in html
	assert "location.hash" in script or "loc.hash" in script
	assert '"POST"' in script
	assert "token: key" in script
	assert "?k=" not in script
	assert "?token=" not in script


@pytest.mark.parametrize("page", PHONE_PAGES)
def test_given_phone_page_when_read_then_it_loads_the_auth_guard(page: str) -> None:
	# given
	path = _STATIC / page
	# when
	html = path.read_text(encoding="utf-8")
	# then
	assert '<script type="module" src="/static/js/auth-guard.js"></script>' in html


def test_given_clear_preferences_when_run_then_passcode_record_survives(tmp_path: Path) -> None:
	# given
	prefs = JsonUserPreferences(tmp_path / "preferences.json")
	prefs.set_compress_media(True)
	store = JsonPasscodeStore(tmp_path / "network_passcode.json")
	record = PasscodeRecord(salt=b"s" * 16, passcode_hash=b"h" * 32, token_secret=b"t" * 32)
	store.save(record)
	# when
	prefs.clear()
	# then
	assert store.load() == record


def test_given_data_dir_when_paths_resolved_then_passcode_file_is_separate_from_preferences() -> None:
	# given
	passcode_file = network_passcode_path()
	# when
	preferences_file = user_preferences_path()
	# then
	assert passcode_file != preferences_file
	assert passcode_file.name == "network_passcode.json"


def test_given_home_page_when_read_then_dock_has_open_and_active_controls_and_info_panel() -> None:
	# given
	html = (_STATIC / "index.html").read_text(encoding="utf-8")
	# when
	ids = [
		'id="passcode-dock"',
		'id="passcode-input"',
		'id="btn-passcode-set"',
		'id="btn-passcode-change"',
		'id="btn-passcode-clear"',
		'id="btn-passcode-info"',
		'id="passcode-info-panel"',
	]
	# then
	assert all(marker in html for marker in ids)
	assert "Not set — anyone on your Wi-Fi can open the Gallery." in html
	assert "Not encryption" in html


def test_given_dock_styles_when_read_then_width_and_narrow_layout_match_wireframe() -> None:
	# given
	css = (_STATIC / "shell-components.css").read_text(encoding="utf-8")
	# when
	has_width = "width: 16.5rem" in css
	has_narrow = (
		"@media (max-width: 640px)" in css and ".passcode-dock { left: 0.5rem; right: 0.5rem; width: auto; }" in css
	)
	# then
	assert has_width
	assert has_narrow
