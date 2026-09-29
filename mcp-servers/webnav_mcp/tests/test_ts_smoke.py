"""Live smoke: the real typescript-language-server serving `.ts` files.

Skipped when the server binary isn't installed locally (`npm ci`). Marked
integration like codenav's ty smoke so fast unit runs can exclude it.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import pytest
from mcp_nav_shared.lsp_client import LspClient
from webnav_mcp.lang_command import resolve_ts_command
from webnav_mcp.server import _SCRIPT_LANGUAGE_IDS


pytestmark = pytest.mark.integration

# tests/test_ts_smoke.py -> webnav_mcp -> mcp-servers -> repo root (node_modules lives there).
_REPO_ROOT = Path(__file__).resolve().parents[3]

_TS_SERVER_AVAILABLE = (
	(_REPO_ROOT / "node_modules" / ".bin" / "typescript-language-server").is_file()
	and (_REPO_ROOT / "node_modules" / "typescript").is_dir()
) or shutil.which("typescript-language-server") is not None


def _client(workspace: Path) -> LspClient:
	return LspClient(
		workspace_root=workspace,
		command=resolve_ts_command(_REPO_ROOT),
		language_id="javascript",
		language_ids=_SCRIPT_LANGUAGE_IDS,
	)


@pytest.mark.skipif(not _TS_SERVER_AVAILABLE, reason="typescript-language-server not installed (npm ci)")
def test_given_ts_type_error_when_diagnostics_then_first_call_reports_it(tmp_path):
	# given — tsserver has no pull diagnostics; the push must be awaited, not skipped
	bad = tmp_path / "bad.ts"
	bad.write_text('export const n: number = "str";\n', encoding="utf-8")
	good = tmp_path / "good.ts"
	good.write_text("export const ok: number = 1;\n", encoding="utf-8")
	client = _client(tmp_path)

	async def _run() -> None:
		await client.start()
		try:
			# when
			bad_items = await client.diagnostics(str(bad))
			good_items = await client.diagnostics(str(good))
			# then
			assert any(item.get("code") == 2322 for item in bad_items), bad_items
			assert good_items == []
		finally:
			await client.stop()

	asyncio.run(_run())


@pytest.mark.skipif(not _TS_SERVER_AVAILABLE, reason="typescript-language-server not installed (npm ci)")
def test_given_edited_ts_file_when_diagnostics_then_reflects_new_content(tmp_path):
	# given
	src = tmp_path / "edit.ts"
	src.write_text("export const n: number = 1;\n", encoding="utf-8")
	client = _client(tmp_path)

	async def _run() -> None:
		await client.start()
		try:
			assert await client.diagnostics(str(src)) == []
			# when — introduce an error (different size, so ensure_open re-syncs)
			src.write_text('export const n: number = "now a string";\n', encoding="utf-8")
			items = await client.diagnostics(str(src))
			# then
			assert any(item.get("code") == 2322 for item in items), items
		finally:
			await client.stop()

	asyncio.run(_run())


@pytest.mark.skipif(not _TS_SERVER_AVAILABLE, reason="typescript-language-server not installed (npm ci)")
def test_given_ts_files_when_hover_and_references_then_typed_and_cross_file(tmp_path):
	# given
	lib = tmp_path / "lib.ts"
	lib.write_text("export function greet(name: string): string {\n\treturn name;\n}\n", encoding="utf-8")
	use = tmp_path / "use.ts"
	use.write_text('import { greet } from "./lib.ts";\n\ngreet("x");\n', encoding="utf-8")
	client = _client(tmp_path)

	async def _run() -> None:
		await client.start()
		try:
			await client.ensure_open(str(use))
			# when
			hover = await client.hover(str(lib), 1, 18)
			refs = await client.references(str(lib), 1, 18)
			# then
			assert "greet(name: string): string" in str(hover)
			assert any(str(r["uri"]).endswith("use.ts") for r in refs), refs
		finally:
			await client.stop()

	asyncio.run(_run())
