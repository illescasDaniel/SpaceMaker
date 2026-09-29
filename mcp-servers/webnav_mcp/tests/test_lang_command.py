"""Tests for Windows-aware npm `.bin` resolution."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from webnav_mcp.lang_command import resolve_css_command, resolve_html_command, resolve_ts_command


def _touch(path: Path) -> Path:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text("", encoding="utf-8")
	return path


def test_prefers_cmd_shim_on_windows(tmp_path: Path) -> None:
	shim = _touch(tmp_path / "node_modules" / ".bin" / "typescript-language-server")
	cmd = _touch(tmp_path / "node_modules" / ".bin" / "typescript-language-server.cmd")
	with patch("webnav_mcp.lang_command.sys.platform", "win32"):
		resolved = resolve_ts_command(tmp_path)
	assert resolved == [str(cmd), "--stdio"]
	assert resolved[0] != str(shim)


def test_uses_extensionless_shim_on_posix(tmp_path: Path) -> None:
	shim = _touch(tmp_path / "node_modules" / ".bin" / "typescript-language-server")
	_touch(tmp_path / "node_modules" / ".bin" / "typescript-language-server.cmd")
	with patch("webnav_mcp.lang_command.sys.platform", "linux"):
		resolved = resolve_ts_command(tmp_path)
	assert resolved == [str(shim), "--stdio"]


def test_falls_back_to_which_then_npx(tmp_path: Path) -> None:
	with (
		patch("webnav_mcp.lang_command.sys.platform", "win32"),
		patch(
			"webnav_mcp.lang_command.shutil.which",
			side_effect=lambda name: {
				"typescript-language-server": None,
				"npx": r"C:\Program Files\nodejs\npx.cmd",
			}.get(name),
		),
	):
		resolved = resolve_ts_command(tmp_path)
	assert resolved == [
		r"C:\Program Files\nodejs\npx.cmd",
		"--yes",
		"-p",
		"typescript@5",
		"-p",
		"typescript-language-server",
		"typescript-language-server",
		"--stdio",
	]


@pytest.mark.parametrize(
	("resolver", "bin_name"),
	[
		(resolve_html_command, "vscode-html-language-server"),
		(resolve_css_command, "vscode-css-language-server"),
	],
)
def test_html_css_also_prefer_cmd(tmp_path: Path, resolver, bin_name: str) -> None:
	cmd = _touch(tmp_path / "node_modules" / ".bin" / f"{bin_name}.cmd")
	_touch(tmp_path / "node_modules" / ".bin" / bin_name)
	with patch("webnav_mcp.lang_command.sys.platform", "win32"):
		assert resolver(tmp_path) == [str(cmd), "--stdio"]
