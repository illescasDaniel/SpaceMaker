# codenav-mcp

MCP server for type-resolved Python navigation, backed by
[ty](https://github.com/astral-sh/ty)'s language server. Definitions,
references, and call sites go through real inference (imports, DI
parameters, dataclass fields), not text grep.

## Tools

**Prefer intent-level (name-based) tools first:**

| Tool | Answers |
|------|---------|
| `symbol_info` | What is this? Header + hover + definition + references |
| `outline` | What's in this file? (classes, methods, functions) |
| `callers` | Who actually calls this function? (call hierarchy, not imports) |
| `implementations` | Which classes structurally implement this `Protocol`? |
| `search_symbol` | Workspace symbol search by name (ranked, capped) |

Then position tools when you already have a `path:line:col`:

| Tool | Answers |
|------|---------|
| `hover` | Type / docs at a position |
| `definition` | Go to definition (DI-aware) |
| `references` | All usages across the workspace |
| `diagnostics` | ty type-check diagnostics for one file |

`name` and `query` are accepted as aliases on the name-based tools
(`port_name` / `name` / `query` on `implementations`). A missing/wrong
param yields a soft hint instead of a validation wall. Dotted names may nest
(`Outer.Inner.method`); `implementations` also takes `file_path` to pick one
port when the name exists in several files, and counts inherited members and
dataclass/`self.x` fields toward a port's required names.

Positions are **1-indexed**. `column` is a UTF-16 character offset (a leading
tab counts as one character).

Python only (`.py` / `.pyi`).

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
| `CODENAV_MCP_WORKSPACE` | unset → follows the client's MCP roots when they name a worktree of the same repo, else `CLAUDE_PROJECT_DIR`/cwd | Pins the project root (never overridden). See the `workspace` tool |
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
