"""Contract tests for Components UI helpers (no JS test harness in-repo)."""

from pathlib import Path


_REPO = Path(__file__).resolve().parents[2]
_SETUP_TS = _REPO / "web" / "src" / "components-setup.ts"
_SETTINGS_TS = _REPO / "web" / "src" / "settings.ts"
_SHELL_TS = _REPO / "web" / "src" / "shell.ts"


def test_given_components_setup_module_when_read_then_poll_interval_is_3s():
	# given
	text = _SETUP_TS.read_text(encoding="utf-8")
	# when / then
	assert "export const COMPONENTS_POLL_MS = 3000;" in text
	assert "view-components" in text
	assert "detailsExpandedForSummary" in text


def test_given_settings_when_read_then_uses_poll_helpers():
	# given
	text = _SETTINGS_TS.read_text(encoding="utf-8")
	# when / then
	assert "COMPONENTS_POLL_MS" in text
	assert "shouldRunComponentsPoll" in text
	assert "detailsExpandedForSummary" in text
	assert "details_expanded" in text
	assert 'apiGet<ManagedToolsStatus>("/api/tools/status")' in text or 'apiGet("/api/tools/status")' in text


def test_given_shell_when_show_view_then_syncs_components_poll():
	# given
	text = _SHELL_TS.read_text(encoding="utf-8")
	# when / then
	assert "syncComponentsPollForView" in text


def test_given_components_index_when_read_then_lead_copy_is_short():
	# given
	html = (_REPO / "src" / "spacemaker" / "adapters" / "inbound" / "web" / "static" / "index.html").read_text(
		encoding="utf-8",
	)
	# when / then
	assert "Tools download when possible." in html
	assert "Continue reloads PATH." in html
	assert "SpaceMaker downloads pinned tools when it can." not in html
