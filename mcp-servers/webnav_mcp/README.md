# webnav-mcp

An MCP server that gives AI agents JS/TS/HTML/CSS navigation, plus a
cross-file index of CSS custom properties and `#id`/`.class` selectors that
single-file language servers can't provide. It's the front-end counterpart to
[`codenav-mcp`](https://pypi.org/project/codenav-mcp/).

## Quick start

You need [uv](https://docs.astral.sh/uv/) (or `pipx`) and Node.js with `npx`:

```bash
uvx webnav-mcp
```

Register it with your MCP host. For Claude Code, from the project root:

```bash
claude mcp add webnav -- uvx webnav-mcp
```

Or add it to a project `.mcp.json` (Claude Code) or `.cursor/mcp.json` (Cursor):

```json
{
	"mcpServers": {
		"webnav": {
			"command": "uvx",
			"args": ["webnav-mcp"]
		}
	}
}
```

In Cursor, also set `"env": {"WEBNAV_MCP_WORKSPACE": "${workspaceFolder}"}`,
because Cursor may start MCP servers with your home directory as the working
directory.

## Language servers

Requests are routed to three Node language servers by file extension:

| Extension | Backend |
|-----------|---------|
| `.js` / `.mjs` / `.cjs` / `.jsx` / `.ts` / `.mts` / `.cts` / `.tsx` | `typescript-language-server` (JS via `allowJs` / `jsconfig.json`) |
| `.html` | `vscode-html-language-server` |
| `.css` | `vscode-css-language-server` |

Each binary is looked up in the project's `node_modules/.bin/`, then on
`PATH`. If neither has it, webnav falls back to `npx --yes`, which downloads it
on first use (the TypeScript fallback also pulls in `typescript@5`, a peer
dependency the server doesn't bundle). To skip the download, install them in
your project:

```bash
npm install --save-dev typescript typescript-language-server vscode-langservers-extracted
```

## Tools

**For JS/TS, start with the name-based tools:**

| Tool | Answers |
|------|---------|
| `symbol_info` | What is this? Header, hover, definition and references in one call |
| `outline` | What's in this file? (source order; locals left out unless `detailed=true`) |
| `search_symbol` | JS/TS workspace symbol search (ranked, capped; optional `kind=` / `path=` filters; fuzzy-only hits summarised unless `fuzzy=true`) |
| `workspace` | Which directory is being navigated, and why |

Then use the position tools once you have a `path:line:col`:

| Tool | Answers |
|------|---------|
| `hover` | Type and docs at a position |
| `definition` | Go to definition (CSS/HTML tokens answer from the index below) |
| `references` | All usages (CSS/HTML tokens answer from the index below) |
| `diagnostics` | Language-server diagnostics; CSS/HTML also get unreferenced-selector and undefined-variable warnings |

**Cross-file CSS/HTML index** (a Python scanner, not the language servers):

| Tool | Answers |
|------|---------|
| `css_var` | Where is `--name` defined and used? |
| `selector` | Where is `#id` or `.class` defined and used (CSS, HTML, JS)? |

`search_symbol`, `symbol_info` and `outline` are **JS/TS only**. Use
`css_var` and `selector` for markup and stylesheets.

`name` and `query` are accepted as aliases of each other on the name-based
tools. A missing parameter gets a short hint back instead of a validation
error.

Positions are **1-indexed**. `column` is a UTF-16 character offset (a leading
tab counts as one character).

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `WEBNAV_MCP_WORKSPACE` | unset: follows the client's MCP roots when they name a worktree of the same git repository, else `CLAUDE_PROJECT_DIR`, else the working directory | Pins the project root (never overridden). See the `workspace` tool |
| `WEBNAV_MCP_ROOTS` | the whole workspace as one root, labelled `web` | Comma-separated `label=relative/path` pairs to index separately, e.g. `app=src,prototypes=design` when two trees define their own values |
| `WEBNAV_MCP_EXCLUDE` | nothing | Comma-separated workspace-relative paths of generated script output (e.g. the JS a TS build emits). These aren't opened, are hidden from `search_symbol`, and are rejected by the position tools. The CSS/selector index still reads them |

## Requirements

- Python ≥ 3.11
- Node.js (for the language servers; see above)
- Installed automatically: [`mcp`](https://pypi.org/project/mcp/),
  [`mcp-nav-shared`](https://pypi.org/project/mcp-nav-shared/)

## Related

- Design notes (index heuristics, dynamic selectors, positioning):
  [docs/agent-tooling.md](https://github.com/illescasDaniel/SpaceMaker/blob/main/docs/agent-tooling.md).

## Development

Developed in the [SpaceMaker](https://github.com/illescasDaniel/SpaceMaker)
repository as a uv workspace member (`mcp-servers/webnav_mcp`). From a
checkout: `uv sync --group dev`, then `uv run webnav-mcp`.

## License

MIT. See [LICENSE](https://github.com/illescasDaniel/SpaceMaker/blob/main/mcp-servers/webnav_mcp/LICENSE).
