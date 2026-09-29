"""Fast unit tests for `mcp_nav_shared.workspace`."""

from __future__ import annotations

from mcp_nav_shared.workspace import resolve_source_root, resolve_workspace_root


def test_given_explicit_env_when_resolve_workspace_root_then_prefers_it(tmp_path, monkeypatch):
	# given
	override = tmp_path / "override"
	override.mkdir()
	fallback = tmp_path / "fallback"
	fallback.mkdir()
	monkeypatch.setenv("CODENAV_MCP_WORKSPACE", str(override))
	monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(fallback))
	# when
	root = resolve_workspace_root("CODENAV_MCP_WORKSPACE")
	# then
	assert root == override.resolve()


def test_given_claude_project_dir_when_no_explicit_env_then_uses_claude(tmp_path, monkeypatch):
	# given
	claude = tmp_path / "claude-root"
	claude.mkdir()
	monkeypatch.delenv("CODENAV_MCP_WORKSPACE", raising=False)
	monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(claude))
	# when
	root = resolve_workspace_root("CODENAV_MCP_WORKSPACE")
	# then
	assert root == claude.resolve()


def test_given_no_env_when_resolve_workspace_root_then_uses_cwd(tmp_path, monkeypatch):
	# given — no explicit override and no host-injected project dir: the
	# server must fall back to wherever it was actually launched (its own
	# install location, e.g. a repo it ships from, is never the right guess
	# for a different project's checkout).
	monkeypatch.delenv("CODENAV_MCP_WORKSPACE", raising=False)
	monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
	monkeypatch.chdir(tmp_path)
	# when
	root = resolve_workspace_root("CODENAV_MCP_WORKSPACE")
	# then
	assert root == tmp_path.resolve()


def test_given_explicit_source_root_env_when_resolve_source_root_then_used(tmp_path, monkeypatch):
	# given
	monkeypatch.setenv("SOME_SOURCE_ROOT", "src")
	# when
	root = resolve_source_root("SOME_SOURCE_ROOT", tmp_path)
	# then
	assert root == (tmp_path / "src").resolve()


def test_given_no_source_root_env_when_resolve_source_root_then_defaults_to_workspace_root(tmp_path, monkeypatch):
	# given
	monkeypatch.delenv("SOME_OTHER_SOURCE_ROOT", raising=False)
	# when
	root = resolve_source_root("SOME_OTHER_SOURCE_ROOT", tmp_path)
	# then
	assert root == tmp_path
