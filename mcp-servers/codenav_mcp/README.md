# codenav-mcp

MCP server that exposes [ty](https://github.com/astral-sh/ty)'s language-server
features as tools for AI agents. Named `codenav` (not `ty`) because `ty` is
Astral's underlying tool; this package is the MCP wrapper.

## What it does

Type-resolved Python navigation — definitions, references, and call sites
through real inference (imports, DI parameters, dataclass fields), not text
grep.

**Prefer intent-level (name-based) tools first:**

| Tool | Answers |
|------|---------|
| `symbol_info` | What is this? (hover + definition + references) |
| `outline` | What's in this file? |
| `callers` | Who calls this function? |
| `implementations` | Which classes structurally implement this `Protocol`? |

Then position tools when you already have a `path:line:col`:
`search_symbol`, `hover`, `definition`, `references`, `diagnostics`.

Positions are **1-indexed**. `column` is a UTF-16 character offset (a leading
tab counts as one character).

## Dependencies

- Python ≥ 3.11
- [`mcp`](https://pypi.org/project/mcp/)
- [`ty`](https://pypi.org/project/ty/)
- [`mcp-nav-shared`](../mcp-nav-shared/README.md)

## Run

```bash
# From a SpaceMaker checkout (uv workspace installs the package editable)
uv run python -m codenav_mcp.server
```

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `CODENAV_MCP_WORKSPACE` | inferred from install / `CLAUDE_PROJECT_DIR` | Project root for the language server |
| `CODENAV_MCP_SOURCE_ROOT` | whole workspace | Directory scanned for `implementations` candidates and dotted-import derivation (SpaceMaker sets `src`) |

## Example MCP host config

```json
{
	"mcpServers": {
		"codenav": {
			"command": "uv",
			"args": ["run", "python", "-m", "codenav_mcp.server"],
			"env": {
				"CODENAV_MCP_WORKSPACE": "/path/to/project",
				"CODENAV_MCP_SOURCE_ROOT": "src"
			}
		}
	}
}
```

Adjust `command`/`args` to however your host launches Python packages.

## License

MIT — see [LICENSE](LICENSE).

## Developed in SpaceMaker

SpaceMaker pins workspace/env in `.mcp.json` / `.cursor/mcp.json`. Full agent
reference (Protocol conformance probe, positioning, shared formatters):
[docs/agent-tooling.md](../../docs/agent-tooling.md).
