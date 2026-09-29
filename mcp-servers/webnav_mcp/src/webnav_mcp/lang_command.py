"""Resolves how to launch the Node-based language servers webnav multiplexes to.

Same fallback chain as codenav's `resolve_ty_command`: a locally installed
binary first (here, npm's `node_modules/.bin/`), then PATH, then a
package-manager-mediated run as a last resort.
"""

from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path


logger = logging.getLogger(__name__)


def _local_bin_candidates(workspace_root: Path, bin_name: str) -> list[Path]:
	"""Ordered candidates under `node_modules/.bin` for this platform.

	On Windows, npm writes an extensionless POSIX shim *and* a `.cmd` launcher.
	`CreateProcess` cannot run the shim (WinError 193), so prefer `.cmd`.
	"""
	bin_dir = workspace_root / "node_modules" / ".bin"
	if sys.platform == "win32":
		return [bin_dir / f"{bin_name}.cmd", bin_dir / bin_name]
	return [bin_dir / bin_name]


def _resolve_bin(workspace_root: Path, bin_name: str, npx_args: list[str]) -> list[str]:
	for candidate in _local_bin_candidates(workspace_root, bin_name):
		if candidate.is_file():
			return [str(candidate), "--stdio"]
	on_path = shutil.which(bin_name)
	if on_path:
		return [on_path, "--stdio"]
	logger.warning(
		"%s not found locally (node_modules/.bin) or on PATH; falling back to "
		"'npx --yes %s', which downloads it on first use.",
		bin_name,
		" ".join(npx_args),
	)
	# Bare "npx" fails under CreateProcess on Windows (npx is npx.cmd / npx.ps1).
	npx = shutil.which("npx") or "npx"
	return [npx, "--yes", *npx_args, "--stdio"]


def resolve_ts_command(workspace_root: Path) -> list[str]:
	# typescript-language-server requires "typescript" as a peer dependency
	# it does NOT bundle: `npx --yes typescript-language-server` alone
	# resolves and starts the binary but then fails at LSP `initialize` with
	# "Could not find a valid TypeScript installation" unless the workspace
	# happens to have its own node_modules/typescript. Pulling in "typescript"
	# alongside via `-p` makes the npx fallback self-sufficient. Pinned to the
	# 5.x line: an unpinned `-p typescript` can resolve the 7.x native-compiler
	# preview, which has no lib/tsserverlibrary.js and breaks resolution the
	# same way.
	return _resolve_bin(
		workspace_root,
		"typescript-language-server",
		["-p", "typescript@5", "-p", "typescript-language-server", "typescript-language-server"],
	)


def resolve_html_command(workspace_root: Path) -> list[str]:
	return _resolve_bin(
		workspace_root,
		"vscode-html-language-server",
		["--package=vscode-langservers-extracted", "vscode-html-language-server"],
	)


def resolve_css_command(workspace_root: Path) -> list[str]:
	return _resolve_bin(
		workspace_root,
		"vscode-css-language-server",
		["--package=vscode-langservers-extracted", "vscode-css-language-server"],
	)
