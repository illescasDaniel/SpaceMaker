from spacemaker.bootstrap.ui_shell import CONTENT_SECURITY_POLICY, CONTENT_SECURITY_POLICY_DESKTOP


def test_given_lan_csp_when_inspect_then_no_unsafe_eval():
	assert "unsafe-eval" not in CONTENT_SECURITY_POLICY


def test_given_desktop_csp_when_inspect_then_allows_unsafe_eval_for_pywebview():
	assert "unsafe-eval" in CONTENT_SECURITY_POLICY_DESKTOP


def test_given_csp_strings_when_inspect_then_directives_are_separated():
	for policy in (CONTENT_SECURITY_POLICY, CONTENT_SECURITY_POLICY_DESKTOP):
		assert "'none'script-src" not in policy
		assert "; script-src" in policy
