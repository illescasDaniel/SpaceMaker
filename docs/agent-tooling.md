# Agent tooling reference

Reference material for the AI-agent-facing tooling in this repo: the
`codenav` MCP server, how the Cursor/Claude Code rule pairs are maintained,
and durable gotchas hit while building this tooling. `AGENTS.md` covers the
everyday commands and rules; this page is for when you need more.

## `codenav` MCP server

`mcp-servers/codenav_mcp/` wraps `ty server` (Astral's type checker running
as a language server) as MCP tools: `search_symbol`, `definition`,
`references`, `hover`, `diagnostics`. It's named `codenav`, not `ty`, since
`ty` is Astral's name for the underlying tool it wraps, not this project's
server.

It's a purpose-built client, not a generic LSP bridge: `mcp-language-
server`'s name-based `definition`/`references` tools were tried first and
don't resolve symbols against `ty`, even though `ty`'s own `workspace/
symbol` implementation answers those same queries correctly when asked
directly over LSP. Run it standalone for manual testing with `uv run python
mcp-servers/codenav_mcp/server.py`; point it at a different workspace via
the `CODENAV_MCP_WORKSPACE` env var (defaults to the current working
directory).

The generic JSON-RPC/LSP wire protocol (subprocess framing, request/
response dispatch, document sync) lives in `mcp-servers/_shared/lsp_client.py`
as `LspClient`, shared with `webnav` below. Only the `ty`-specific launch
command (`mcp-servers/codenav_mcp/ty_command.py`) and languageId are
codenav's own.

## `webnav` MCP server

`mcp-servers/webnav_mcp/` gives the same kind of navigation for the
project's JS/HTML/CSS (`search_symbol`, `definition`, `references`, `hover`,
`diagnostics`), multiplexing three Node-based language servers behind one
MCP tool set, routed by file extension:

- `.js`/`.mjs`/`.cjs` → `typescript-language-server` (via `allowJs`/
  `jsconfig.json` at the repo root — no TypeScript conversion needed)
- `.html` → `vscode-html-language-server`
- `.css` → `vscode-css-language-server`

Both come from the `vscode-langservers-extracted` npm package. `npm install`
(already required for Biome) pulls all three binaries into `node_modules/
.bin/`; `mcp-servers/webnav_mcp/lang_command.py` resolves them there first,
falling back to `PATH` and then `npx` — same fallback chain as codenav's ty
resolver.

`search_symbol` only covers JS: the HTML/CSS language servers don't
implement a useful `workspace/symbol`. `jsconfig.json` has `checkJs: false`
by default (the existing `app.js` is large and untyped; flip it per-file
with a `// @ts-check` comment to opt a file into stricter `diagnostics`).
Run it standalone for manual testing with `uv run python
mcp-servers/webnav_mcp/server.py`; point it at a different workspace via
the `WEBNAV_MCP_WORKSPACE` env var.

## Rules — Cursor vs Claude Code

Both tools read `AGENTS.md` as project instructions. Path-scoped rules
(guidance that should load only when a matching file is in play, not on
every turn) live as a hand-maintained pair per rule, kept in two parallel
directories:

- `.cursor/rules/*.mdc` — Cursor's format: YAML frontmatter with
  `description`/`globs`/`alwaysApply`.
- `.claude/rules/*.md` — Claude Code's format (see
  [Claude Code's rules docs](https://code.claude.com/docs/en/memory#organize-rules-with-claude/rules/)):
  plain markdown with a `paths` frontmatter field for path scoping.

**These are hand-maintained duplicates, not symlinks.** A symlink was tried
first and rejected: Claude Code only discovers files with a literal `.md`
extension, so a symlink pointing at a `.mdc` file (even one renamed to end in
`.md`) was not picked up in this environment — plain copies in the native
format were required instead.

**The two rule directories must stay equivalent** — same body, equivalent
scoping (Cursor `alwaysApply: true` ⇔ a Claude rule with no `paths`; Cursor
`alwaysApply: false` + `globs` ⇔ Claude `paths` with the same patterns). No
Cursor-only rule kinds (description-only "agent requested" rules, manual
rules) are used, since Claude Code has no equivalent. `tests/unit/test_agent_context.py`
enforces this pairing and scoping as part of `uv run task checks` — a
mismatch is a bug, not an intentional fork. When editing a rule, edit both
copies together.

Skills are shared without duplication: Claude Code discovers
`.cursor/skills/` via the real OS symlink `.claude/skills -> ../.cursor/skills`
(relative target, portable across machines/OS; `git checkout` recreates it
correctly on any clone). To recreate manually on Windows, use
`cmd /c "mklink /D skills ..\.cursor\skills"` from inside `.claude/` — not
`New-Item -ItemType SymbolicLink`, which can mistype it as a file symlink
(untraversable by `cd`/Explorer) even for a valid directory target.

## Windows / tooling gotchas

- An earlier `docs/architecture.md` (lowercase) collided case-insensitively
  with `docs/ARCHITECTURE.md` on this Windows filesystem and briefly
  overwrote it — recovered from git history and merged. Watch for this with
  any new doc filename differing only by case.
