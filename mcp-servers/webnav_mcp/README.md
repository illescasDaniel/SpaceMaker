# webnav-mcp

MCP server for JS/TS/HTML/CSS navigation — the counterpart to
[`codenav-mcp`](../codenav_mcp/README.md) for front-end and markup assets.

## What it does

Same tool shape as `codenav`, multiplexing three Node language servers by
extension:

| Extension | Backend |
|-----------|---------|
| `.js` / `.mjs` / `.cjs` / `.ts` / `.mts` / `.cts` | `typescript-language-server` (JS via `allowJs` / `jsconfig.json`; TS sent with the `typescript` languageId) |
| `.html` | `vscode-html-language-server` |
| `.css` | `vscode-css-language-server` |

Binaries come from `vscode-langservers-extracted` (typically under
`node_modules/.bin/` after `npm install`).

**Cross-file CSS index** (pure-Python scanner, not the language servers):

| Tool | Answers |
|------|---------|
| `css_var` | Where is `--name` defined / used? |
| `selector` | Where is `#id` or `.class` defined / used (CSS, HTML, JS)? |

`references` / `definition` / `diagnostics` also enrich from this index when
the token under the cursor is a custom property or selector.

`search_symbol` is **JS/TS-only** — the HTML/CSS servers do not implement useful
workspace symbol search.

Positions are **1-indexed**. `column` is a UTF-16 character offset (a leading
tab counts as one character).

## Dependencies

- Python ≥ 3.11
- [`mcp`](https://pypi.org/project/mcp/)
- [`mcp-nav-shared`](../mcp-nav-shared/README.md)
- Node packages providing the language servers (e.g.
  `vscode-langservers-extracted`, `typescript-language-server`) on `PATH` or
  under `node_modules/.bin/` — otherwise falls back to `npx` on first use
  (`typescript-language-server`'s npx fallback also pulls in `typescript@5`,
  since it needs TypeScript as a peer dependency it doesn't bundle)

## Run

```bash
# From a SpaceMaker checkout (uv workspace installs the package editable)
uv run python -m webnav_mcp.server
```

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `WEBNAV_MCP_WORKSPACE` | inferred from install / `CLAUDE_PROJECT_DIR` | Project root |
| `WEBNAV_MCP_EXCLUDE` | nothing | Comma-separated workspace-relative paths of generated script output (e.g. the JS a TS build emits): not opened, hidden from `search_symbol`, rejected by position tools. Does not affect the CSS/selector index |
| `WEBNAV_MCP_ROOTS` | one unnamed root = whole workspace | Comma-separated `label=relative/path` pairs to index separately (SpaceMaker sets `static=…,wireframes=…`) |

## Example MCP host config

```json
{
	"mcpServers": {
		"webnav": {
			"command": "uv",
			"args": ["run", "python", "-m", "webnav_mcp.server"],
			"env": {
				"WEBNAV_MCP_WORKSPACE": "/path/to/project",
				"WEBNAV_MCP_ROOTS": "static=src/path/to/static,wireframes=wireframes"
			}
		}
	}
}
```

Adjust `command`/`args` to however your host launches Python packages.

## License

MIT — see [LICENSE](LICENSE).

## Developed in SpaceMaker

SpaceMaker pins workspace/roots in `.mcp.json` / `.cursor/mcp.json`. Full agent
reference (index heuristics, dynamic selectors, positioning):
[docs/agent-tooling.md](../../docs/agent-tooling.md).
