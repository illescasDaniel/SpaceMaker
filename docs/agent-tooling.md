# Agent tooling reference

Reference material for the AI-agent-facing tooling in this repo: the
`codenav` and `webnav` MCP servers, how the Cursor/Claude Code rule pairs
are maintained, and durable gotchas hit while building this tooling.
`AGENTS.md` covers the everyday commands and rules; this page is for when
you need more. Package-level READMEs under `mcp-servers/*/README.md` are
aimed at standalone consumers; SpaceMaker-specific wiring stays here.

## At a glance

| Server | Language surface | Backend | Start here | This repo's roots |
|--------|------------------|---------|------------|-------------------|
| [`codenav`](../mcp-servers/codenav_mcp/README.md) | Python (`.py`/`.pyi`) | `ty` language server | `symbol_info`, `outline`, `callers`, `implementations` | `CODENAV_MCP_SOURCE_ROOT=src` |
| [`webnav`](../mcp-servers/webnav_mcp/README.md) | JS / TS / HTML / CSS | `typescript-language-server` + vscode HTML/CSS servers | `css_var`, `selector`; then position tools | `WEBNAV_MCP_ROOTS` → `web/src` + `static/` + `wireframes/` |

Shared helpers: [`mcp-nav-shared`](../mcp-servers/mcp-nav-shared/README.md).

## MCP config — Cursor vs Claude Code

`codenav` and `webnav` are registered in two host-specific config files
(intentional duplicates, not a symlink — each host has different path
interpolation):

| File | Host | Path / project root |
|------|------|---------------------|
| `.mcp.json` | Claude Code | `${CLAUDE_PROJECT_DIR:-.}` |
| `.cursor/mcp.json` | Cursor | `${workspaceFolder}` |

Both pin `uv run --directory …` and the matching
`CODENAV_MCP_WORKSPACE` / `WEBNAV_MCP_WORKSPACE` env vars. Cursor has been
observed spawning project MCP stdio with cwd set to `$HOME`, so relative
script paths alone fail there; Claude expands `${CLAUDE_PROJECT_DIR:-.}`
and usually uses the project as cwd. When editing launch args or env for
these servers, update **both** files together (same servers, different
placeholders).

Workspace root inside the Python servers is resolved by
`mcp-servers/mcp-nav-shared/src/mcp_nav_shared/workspace.py`: explicit `CODENAV_MCP_WORKSPACE` /
`WEBNAV_MCP_WORKSPACE`, then `CLAUDE_PROJECT_DIR`, then the repo root
inferred from that module's path (so a wrong spawn cwd cannot break
indexing).

Both servers are written to be reusable outside this repo (they may ship as
standalone tools for other projects some day), so every SpaceMaker-specific
assumption is pushed into **this repo's own `.mcp.json`/`.cursor/mcp.json`
env vars**, not hardcoded in the server source — following the same
override-with-sane-default shape as `CODENAV_MCP_WORKSPACE`/
`WEBNAV_MCP_WORKSPACE` above:

| Env var | Server | Default (generic) | This repo's value |
|---|---|---|---|
| `CODENAV_MCP_SOURCE_ROOT` | codenav | the whole workspace | `src` (scopes/speeds up `implementations`' class scan and import-path derivation) |
| `WEBNAV_MCP_ROOTS` | webnav | one unnamed root spanning the whole workspace | `web=web/src,static=src/spacemaker/adapters/inbound/web/static,wireframes=wireframes` (TS sources, production assets, UX wireframes) |

A project that unsets these gets a working, if less scoped/labeled, default
rather than an error or a SpaceMaker-shaped assumption.

## Package layout (uv workspace)

`mcp-servers/` is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/)
(`[tool.uv.workspace]` in the root `pyproject.toml`), not just a folder of
scripts — each server is its own installable package, so either can be
released standalone later without restructuring:

- [`mcp-servers/mcp-nav-shared/`](../mcp-servers/mcp-nav-shared/README.md) →
  distribution `mcp-nav-shared`, import name `mcp_nav_shared`. No runtime
  deps; shared LSP client, symbol resolution, formatting, and
  workspace-root discovery.
- [`mcp-servers/codenav_mcp/`](../mcp-servers/codenav_mcp/README.md) →
  distribution `codenav-mcp`, import name `codenav_mcp`. Depends on
  `mcp-nav-shared` via `tool.uv.sources` (`{ workspace = true }`),
  resolved to the local sibling rather than PyPI.
- [`mcp-servers/webnav_mcp/`](../mcp-servers/webnav_mcp/README.md) →
  distribution `webnav-mcp`, import name `webnav_mcp`. Same
  `mcp-nav-shared` dependency wiring.

Each follows the repo's own `src/<pkg>/` layout and has its own
`pyproject.toml` with a package-local `[tool.pytest.ini_options]`
(`testpaths = ["tests"]`, `pythonpath = ["src"]`) — necessary because pytest
walks upward for the nearest ini file, and without a local one a bare
`pytest` run from inside e.g. `mcp-servers/codenav_mcp/` would pick up the
root's `testpaths = ["tests"]` instead. The root project depends on both
servers as dev dependencies (also workspace-sourced), and `uv sync` installs
all three editable into the one shared venv — this is what lets
`.mcp.json`/`.cursor/mcp.json` launch them as `python -m codenav_mcp.server`
/ `python -m webnav_mcp.server` (proper package imports, no `sys.path`
hacks) and lets each package's `tests/` run standalone from its own
directory as well as from the repo root.

## Why no MCP prompts/resources

Neither server exposes MCP prompts or resources, and this is deliberate, not
an oversight. Prompts are **user-invoked** (they surface as
`/mcp__codenav__…` slash commands): the agent never calls them, so they
can't make tool calls better. Resources are static data the model has to
explicitly fetch, which adds a lookup step for no benefit over just
returning richer text from a tool. What actually shapes agent behavior is
the server `instructions` string and each tool's docstring, since both
already load into context — leverage comes from better-composed tools (see
`symbol_info`/`outline`/`callers`/`implementations` and `css_var`/`selector`
below), not from templates the agent has to know to ask for.

## `codenav` MCP server

`mcp-servers/codenav_mcp/` wraps `ty server` (Astral's type checker running
as a language server) as MCP tools. It's named `codenav`, not `ty`, since
`ty` is Astral's name for the underlying tool it wraps, not this project's
server.

**Start with the intent-level tools, drop to position tools for specifics.**
The LSP mirrors position-based lookups 1:1, which forces an agent to
`search_symbol`, work out a tab-aware column, then call `hover`/`definition`/
`references` separately just to answer "what does this do" or "who calls
this". Four composite tools answer those questions in one call, all
name-based (no column arithmetic) via the shared `resolve_symbol()` helper
in `mcp-servers/mcp-nav-shared/src/mcp_nav_shared/resolve.py`:

- **`symbol_info(name, file_path=None, include_references=True)`** — the
  default first call for "what is this": header, hover text (signature +
  docstring), definition snippet, and references grouped by file with a
  total count.
- **`outline(file_path)`** — an indented tree of classes/methods/functions
  with line numbers, so an agent can navigate a large file (e.g.
  `services.py`) without reading it end to end.
- **`callers(name, file_path=None)`** — `prepareCallHierarchy` +
  `incomingCalls`: who actually calls this function, with call-site lines.
  Answers "who calls this?" more precisely than `references`, which also
  matches imports and type annotations.
- **`implementations(port_name)`** — see **Protocol conformance** below.

`resolve_symbol()` accepts a dotted `Class.method` query, narrows by
`file_path` when a name is ambiguous, and raises a `SymbolResolutionError`
(a `ToolInputError`) listing candidates rather than guessing when several
symbols share a name.

`hover`/`definition`/`references`/`search_symbol`/`diagnostics` (the
original position-based tools) are unchanged and still useful once a
composite tool has narrowed things down to a specific position.

### `documentSymbol` shape: hierarchical vs flat

`outline` and `resolve_symbol`'s dotted-member lookup both consume
`textDocument/documentSymbol`, whose response shape is capability-negotiated
and not guaranteed: ty may return hierarchical `DocumentSymbol` nodes
(`range`/`selectionRange`/`children`) or flat `SymbolInformation` entries
(`location` only, no nesting), depending on what the client advertised at
`initialize`. `mcp-servers/mcp-nav-shared/src/mcp_nav_shared/lsp_client.py` advertises
`hierarchicalDocumentSymbolSupport: true`, but code that consumes the result
still branches on `is_hierarchical_document_symbols()` (`mcp_nav_shared/format.py`)
rather than assuming one shape — `to_symbol_tree()` normalizes either shape
into one common tree for `outline`, while `mcp_nav_shared/resolve.py`'s dotted
lookup branches directly (it needs the raw `selectionRange`/`range`
precision the normalized tree discards).

### Protocol conformance (`implementations`)

ty's own `implementation`/`typeHierarchy.subtypes` return nothing for this
codebase's hexagonal ports: ports are `Protocol`s and adapters never
explicitly subclass them (`LocalFileSystem` vs `FileSystemPort`), so
structural typing means there's no nominal edge for the language server to
walk. `implementations(port_name)` answers this "which adapters implement
this port?" question — the most common lookup in a hexagonal codebase.

`port_name` must itself resolve to a `Protocol`: `_protocol_class_names()`
parses the defining file with `ast` (`documentSymbol` doesn't expose base
classes) and checks whether the class's bases include `Protocol`,
`typing.Protocol`/`typing_extensions.Protocol`, or a subscripted
`Protocol[T]`. If it doesn't — a plain class like `AppServices` — the tool
returns an explanation instead of a (meaningless) result, pointing at
`symbol_info`/`references` for explicit-subclass lookups.

Answering then happens in two stages:

1. **Candidates**: classes under `SOURCE_ROOT` (see below) whose method
   names, from `documentSymbol`, are a superset of the Protocol's own
   method names — excluding the port itself (same file + name) and any
   candidate that is itself a Protocol (e.g. a narrower Protocol that
   happens to share method names, which would otherwise "implement" a
   broader one).
2. **Verification**: for each candidate, `didOpen` an in-memory probe
   document at `<root>/.codenav_probe.py` (an `LspClient` scratch document —
   `open_scratch_document`/`change_scratch_document`/`close_scratch_document`
   — never written to disk) that imports the candidate and the port and adds
   `def _p(x: Candidate) -> Port: return x`. Pull that document's
   diagnostics via `pull_diagnostics`; no `invalid-return-type` means ty's
   real type checker accepts the candidate as structurally conforming.
   Results are labeled `(type-verified)`.

The candidate scan and webnav's JS-fallback file scan (below) both skip
`.venv`/`node_modules`/`.git`/etc. via the shared `mcp_nav_shared/exclude.py`
— without it, `implementations` used to abort entirely on the first
unreadable or non-UTF-8 file under a `.venv` it walked into.

Firing many `documentSymbol` requests concurrently (`asyncio.gather`) while
building candidates made ty respond with a `"content modified"` LSP error
under load (~86 concurrent requests for this codebase's size); the fix is to
await them sequentially in a loop instead — still well under a second for
this codebase, and it avoids the error entirely.

`SOURCE_ROOT` (the directory `implementations`' candidate scan and
`_module_path`'s dotted-import derivation both work under) is generic by
default — the whole workspace — and overridable per project via
`CODENAV_MCP_SOURCE_ROOT`, the same override-with-default shape as
`CODENAV_MCP_WORKSPACE`. This repo sets it to `src` in `.mcp.json`/
`.cursor/mcp.json` to keep the candidate scan scoped and fast; a file
outside `SOURCE_ROOT` still works for other tools, `_module_path` just
can't derive a dotted import path for it. Nothing SpaceMaker-specific (no
`ports/`-directory exclusion, no `src/` literal) remains in the server
source itself — see "Portability" above.

Name resolution (`resolve_symbol` in `mcp_nav_shared/resolve.py`, used by
`symbol_info`/`callers`/`implementations`) prefers a case-exact match over a
case-insensitive one when both exist for the same query — e.g. `repo_root`
resolves to the module-level function of that exact name rather than tying
with `REPO_ROOT`. Case-insensitive matches are only considered when no
case-exact one is available.

It's a purpose-built client, not a generic LSP bridge: `mcp-language-
server`'s name-based `definition`/`references` tools were tried first and
don't resolve symbols against `ty`, even though `ty`'s own `workspace/
symbol` implementation answers those same queries correctly when asked
directly over LSP. Run it standalone for manual testing with `uv run python
-m codenav_mcp.server`; point it at a different workspace via
the `CODENAV_MCP_WORKSPACE` env var (otherwise falls back as above).

The generic JSON-RPC/LSP wire protocol (subprocess framing, request/
response dispatch, document sync) lives in
`mcp-servers/mcp-nav-shared/src/mcp_nav_shared/lsp_client.py` as `LspClient`, shared with
`webnav` below. Only the `ty`-specific launch command
(`mcp-servers/codenav_mcp/src/codenav_mcp/ty_command.py`) and languageId are
codenav's own. Location formatting (`path:line:col` headers + snippets)
lives in `mcp-servers/mcp-nav-shared/src/mcp_nav_shared/format.py`.

`references` (both servers) uses `format_references()`: at or under
`DEFAULT_REFERENCES_SNIPPET_LIMIT` (8) hits, each gets its own
`path:line:col` header and a short source snippet, same as `definition`.
Above that threshold — a widely-used symbol can have dozens of call sites —
it switches to a compact, file-grouped list with a `(compact list: N > 8
hits)` header and `L<line>:<col>` entries per file instead of full snippets,
so a single broad query doesn't flood the response; the line:col pairs are
still enough to follow up with a targeted `definition`/`hover` call.

### Positioning (codenav and webnav)

`line` and `column` are **1-indexed**. `column` is a UTF-16 **character
offset** on the line — not a visual/display column. A leading `\t` counts
as **one** character, so after a single tab the next character starts at
column 2. Prefer `search_symbol` (returns `Name  [Kind]  (path:line:col)`)
and pass those numbers through unchanged; guessing display width from a
tab-expanded editor view will miss the symbol. Search positions target the
**identifier name** (not the `class`/`def`/`function` keyword or a leading
decorator line): when the LSP range starts on `@…`, formatting walks the
range and a short lookahead to the `class`/`def` line. Those positions are
safe to feed into `hover` / `definition` / `references`. ty's symbol search
is fuzzy (subsequence) and unordered, so results are ranked before capping:
exact name → case-insensitive exact → prefix → substring → other fuzzy hits.
Results are capped (default 50) with a trailing “and N more” note when
truncated.
`definition` / `references` headers use the same `path:line:col` form so
agents can copy positions into follow-up calls.

JSON-RPC errors from the language server are surfaced as tool text
(`LSP error on …`) rather than looking like empty “not found” results.
Other expected failures — missing file, non-UTF-8 file, unsupported
extension (webnav), request timeout, language server exited — are also
returned as text (`mcp_nav_shared/errors.py`) instead of the MCP framework's opaque
“Error executing tool”. If the language server process dies, in-flight
requests fail immediately and the next tool call starts a fresh one.

`pyproject.toml` lists each `mcp-servers/*/src` directory as a ty `root`, so
tests importing `mcp_nav_shared` / `codenav_mcp` / `webnav_mcp` resolve (clean `ty
check`, and codenav `references` include test usages).
`diagnostics` falls back to the push `publishDiagnostics` cache when pull
diagnostics are unsupported or empty (common for HTML/CSS servers).
All four positional tools reject non-Python files (`.py`/`.pyi` only) up
front with a `ToolInputError` — ty otherwise mis-parses e.g. a `.md` file as
Python and `diagnostics` returns a wall of bogus syntax errors for it.
`diagnostics` (both servers) is capped the same way as `search_symbol`
(`format_diagnostics`, `DEFAULT_DIAGNOSTICS_LIMIT = 200` in
`mcp_nav_shared/format.py`), with a trailing "… and N more" line, so a badly
broken file can't flood the caller either.

## `webnav` MCP server

`mcp-servers/webnav_mcp/` gives the same kind of navigation for the
project's JS/TS/HTML/CSS (`search_symbol`, `definition`, `references`, `hover`,
`diagnostics`), multiplexing three Node-based language servers behind one
MCP tool set, routed by file extension:

- `.ts`/`.js`/`.mjs`/`.cjs` → `typescript-language-server` (shell sources in
  `web/src/` via strict `web/tsconfig.json`; emitted `static/js/*.js` still
  indexed for runtime debugging; `jsconfig.json` includes both)
- `.html` → `vscode-html-language-server`
- `.css` → `vscode-css-language-server`

Both come from the `vscode-langservers-extracted` npm package. `npm ci`
(already required for Biome) pulls all three binaries into `node_modules/
.bin/`; `mcp-servers/webnav_mcp/src/webnav_mcp/lang_command.py` resolves them there first,
falling back to `PATH` and then `npx` — same fallback chain as codenav's ty
resolver. On Windows it prefers the `.cmd` launcher under `.bin/` (the
extensionless npm shim is a POSIX script that `CreateProcess` rejects with
WinError 193); `npx` is resolved via `shutil.which` for the same reason.

**Gotcha:** `typescript-language-server` needs `typescript` as a peer
dependency it does not bundle — it resolves TS from the workspace's own
`node_modules`, not from wherever the server binary itself came from. In a
workspace with no local `typescript` install, `npx --yes
typescript-language-server` alone starts the process but then fails at LSP
`initialize` with "Could not find a valid TypeScript installation". The
`npx` fallback therefore pulls in `-p typescript@5` alongside the server
binary itself — pinned to the 5.x line, since an unpinned `-p typescript`
can resolve the 7.x native-compiler preview, which ships a different
package layout (no `lib/tsserverlibrary.js`) and breaks resolution the same
way.

`search_symbol` only covers JS/TS: the HTML/CSS language servers don't
implement a useful `workspace/symbol`, and webnav does **not** reimplement
general HTML/CSS symbol search. Prefer editing `web/src/*.ts` (strict check
via `npm run check`); emitted `static/js/*.js` is build output. Every module
is fully typed with no `// @ts-nocheck`/`@ts-ignore` escape hatches, calls
other modules via direct named imports (no runtime registry), and writes
relative imports against the real `./x.ts` source file — `tsconfig.json`'s
`rewriteRelativeImportExtensions` rewrites those to `./x.js` in the emitted
output. `biome.json` enforces `noExplicitAny`/`noTsIgnore`/`noVar` as errors
on `web/src/**/*.ts` via a scoped `overrides` entry (not the top-level
`linter.rules`, which would also apply to legacy `wireframes/`/static `.js`
files never meant to be held to that bar), and
`tests/unit/test_web_typing.py` guards the no-nocheck/no-`.js`-import/no-registry
rules at the Python test level.
Run it standalone for manual testing with `uv run python
-m webnav_mcp.server`; point it at a different workspace via
the `WEBNAV_MCP_WORKSPACE` env var (otherwise falls back as above). See
**Positioning** under codenav above — the same column rules apply.

### Workspace-wide CSS var / selector index

The CSS/HTML language servers each see one document at a time, so `var(--x)`
custom-property usages and `#id`/`.class` selectors can't be cross-referenced
across files that way — the most common question for this project's
`--custom-properties` (defined once in `theme.css`, used across every CSS
file, inline `<style>` block and wireframe). `mcp-servers/webnav_mcp/src/
webnav_mcp/web_index.py` answers this with a **pure-Python scanner, not a language
server**: no `@import` resolution, no real CSS parser, regex/brace-stack
grade. It rescans on every call rather than caching — about 20 files total
across both roots, a few ms — so there's no cache-invalidation story to get
wrong.

Which roots get indexed, and under what labels, is generic and
project-configurable via `WEBNAV_MCP_ROOTS` (a comma-separated list of
`label=relative/path` pairs), parsed once in `server.py` and passed into
`web_index.build_workspace_index(workspace_root, roots)`; `web_index.py`
itself has no SpaceMaker-specific paths. Unset, it defaults to a single
unnamed root spanning the whole workspace (minus `node_modules`/`.git`/
`vendor`) — a reasonable default for a project with no such split. **This
repo** sets `WEBNAV_MCP_ROOTS` in `.mcp.json`/`.cursor/mcp.json` to index
two roots **separately**: `src/spacemaker/adapters/inbound/web/static/`
(production, `vendor/` skipped) and `wireframes/` (UX layout truth) — they
define their own values/markup, so mixing them into one answer would be
misleading.

- **`css_var(name)`**: definitions (value + enclosing context, e.g.
  `@media (prefers-color-scheme: dark) › :root`) and usages, grouped by file
  with line numbers, per root.
- **`selector(name)`** (`#id` or `.class`): CSS rule definitions, HTML
  `id=`/`class=` attributes, and JS usages (`getElementById`,
  `classList.add/remove/toggle/contains`, `querySelector`/
  `querySelectorAll`, `className` assignment), grouped by file with line
  numbers, per root.
- **`references`/`definition` fallback**: when the token under the cursor
  in a `.css`/`.html` file is `--name`, `#id` or `.class`, both tools answer
  from this index instead of the single-file language server — this is what
  actually fixes the CSS-var cross-file limitation (confirmed before this
  existed: `--bg` in `theme.css` didn't resolve from a `var(--bg)` usage in
  `shell-gallery.css`, even though both are served together).
- **`diagnostics` enrichment**: for `.css`/`.html` files, index-derived
  warnings are appended to the language server's own diagnostics —
  `var(--x) is never defined in <root>` for usages with no fallback and no
  matching declaration anywhere in that root, and `#id`/`.class is never
  referenced in <root>'s HTML/JS` for a CSS rule with no matching markup or
  script use.

Markup and script are scanned wherever they can plausibly appear: `.html`
files (including their inline `<script>` blocks, at the block's own line
offset — a `<script src="...">` with no inline body is a no-op scan, not a
special case), `.js` files, and also `class="..."`/`id="..."` attributes
embedded inside JS string literals (e.g. `el.innerHTML = '<span
class="gallery-loading-spinner">…'`) — both single- and double-quoted, so
which quote style the surrounding JS string uses doesn't matter. This
matters most for wireframes, which are self-contained HTML with their JS
inline: before inline `<script>` scanning existed, every class/id touched
only from a wireframe's own script looked unreferenced.

Besides a direct `el.className = "..."` assignment, a local variable
conventionally named like a class list (contains `class`/`Class`, e.g.
`mediaClass`) built up with `+=` (`mediaClass += ' slide-in-next-start'`)
is also recorded, tagged `class-var +=` — narrower than matching any
`identifier += 'literal'`, which would flag unrelated string-building code.

A JS selector built from string concatenation (e.g.
`getElementById("view-" + resolved)`, `className = "tool-status
resolution-" + x`, `classList.add("is-" + s)`) is recorded against only its
static string prefix and tagged `dynamic=True`, rather than silently
dropped or guessed at the full runtime value. A dynamic hit **does** count
as a reference for any longer token it's a prefix of:
`unreferenced_selectors()` won't flag `#view-gallery` as unused when
`#view-` has a dynamic hit elsewhere, since the runtime value could
plausibly be that one — this trades a (rare) false negative for not
crying wolf on every dynamically-built id/class in the codebase. The same
`_dynamic_prefix_hits()` lookup surfaces the other direction too:
`selector("#view-components")` lists the `#view-` dynamic hit as a
`dynamic partial match via '#view-'`, since it's a plausible source for
that id at runtime, in addition to any exact hits.

**Known limitations** (accepted, not bugs): selectors built from multiple
concatenated variables, template literals (`` `view-${x}` ``), or
referenced only via inline event-handler attributes (none of these occur in
this codebase) aren't resolved at all. The brace-stack CSS parser doesn't
account for `{`/`}` appearing inside a CSS string value (none occur in this
codebase either).

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

## Subagents — `code-grader` (SDD Phase 5)

`code-grader` is an independent, read-only reviewer that scores finished work against its approved `SPEC.md` (spec conformance with a scenario→test→code map, the four design decisions, hexagonal layering, test quality, UI fidelity, scope discipline, conventions) and returns a PASS / NEEDS WORK scorecard with `path:line` evidence. `sdd-feature` spawns it after Phase 4 is green; the implementer fixes findings (max 2 rounds) and shows the scorecard to the user.

It is a hand-maintained pair like the rules, with **identical bodies and host-specific frontmatter**:

| File | Host | Read-only enforced by | MCP access |
|------|------|-----------------------|------------|
| `.claude/agents/code-grader.md` | Claude Code | `tools:` allow-list (no Edit/Write) | `mcp__codenav`, `mcp__webnav` listed explicitly |
| `.cursor/agents/code-grader.md` | Cursor | `readonly: true` | inherited from the parent |

`tests/unit/test_agent_context.py` enforces matching bodies/name/description and the read-only settings. Edit both copies together.

The mechanical half is `scripts/quality/grade_prechecks.py` (`uv run task grade-prechecks -- --spec specs/<f>/SPEC.md`): hexagonal import guard (hard-fails only for files touched on the branch; legacy violations warn), naming of test functions added on the branch, and SPEC structure (wireframe link resolves, four design decisions answered, every scenario has Given/When/Then). Scenario→test **name matching was tried and dropped**: test names are freeform, and it flagged ~60% of the gallery spec's scenarios as uncovered. The grader maps them by reading instead.

## Windows / tooling gotchas

- An earlier `docs/architecture.md` (lowercase) collided case-insensitively
  with `docs/ARCHITECTURE.md` on this Windows filesystem and briefly
  overwrote it — recovered from git history and merged. Watch for this with
  any new doc filename differing only by case.
- webnav needs a full `npm ci` so `typescript-language-server` /
  `vscode-*-language-server` exist under `node_modules/.bin/`. A partial
  install (Biome only) forces the `npx` fallback, which also fails under
  bare `CreateProcess` unless `npx` is resolved to `npx.cmd`.
