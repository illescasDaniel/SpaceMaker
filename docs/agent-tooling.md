# Agent tooling reference

Reference material for the AI-agent-facing tooling in this repo: the
`codenav` and `webnav` MCP servers, how the Cursor/Claude Code rule pairs
are maintained, and durable gotchas hit while building this tooling.
`AGENTS.md` covers the everyday commands and rules; this page is for when
you need more. `codenav` lives in its own repository
([`codenav-mcp`](https://github.com/illescasDaniel/codenav-mcp), with
[`mcp-nav-shared`](https://github.com/illescasDaniel/mcp-nav-shared)); its README is aimed at standalone
consumers, and SpaceMaker-specific wiring stays here. `webnav` is the TypeScript
package [`webnav-ts-mcp`](https://github.com/illescasDaniel/webnav-ts-mcp) (own repo); the older Python
[`webnav-mcp`](https://github.com/illescasDaniel/webnav-mcp) is no longer used by this repo.

## At a glance

| Server | Language surface | Backend | Start here | This repo's roots |
|--------|------------------|---------|------------|-------------------|
| [`codenav`](https://github.com/illescasDaniel/codenav-mcp) | Python (`.py`/`.pyi`) | `ty` language server | `symbol_info`, `outline`, `callers`, `implementations` | `CODENAV_MCP_SOURCE_ROOT=src` |
| [`webnav`](https://github.com/illescasDaniel/webnav-ts-mcp) (`webnav-ts-mcp`) | JS / TS / HTML / CSS | TypeScript 7 `tsc --lsp --stdio` + vscode HTML/CSS servers | `symbol_info`, `outline`, `callers`, `implementations`, `css_var`, `selector`; then position tools | `WEBNAV_MCP_ROOTS` → `web/src` + `static/` + `wireframes/` |

Shared helpers: [`mcp-nav-shared`](https://github.com/illescasDaniel/mcp-nav-shared).

## MCP config — Cursor vs Claude Code

`codenav` and `webnav` are registered in two host-specific config files
(intentional duplicates, not a symlink — each host has different path
interpolation):

| File | Host | Path / project root |
|------|------|---------------------|
| `.mcp.json` | Claude Code | `${CLAUDE_PROJECT_DIR:-.}` |
| `.cursor/mcp.json` | Cursor | `${workspaceFolder}` |

Both launch codenav with `uvx --from "codenav-mcp>=0.2.0,<0.3" codenav-mcp` (own isolated environment, not a project dependency) and webnav with `npx`; Cursor also pins the matching
`CODENAV_MCP_WORKSPACE` / `WEBNAV_MCP_WORKSPACE` env vars. Cursor has been
observed spawning project MCP stdio with cwd set to `$HOME`, so relative
script paths alone fail there; Claude expands `${CLAUDE_PROJECT_DIR:-.}`
and usually uses the project as cwd. When editing launch args or env for
these servers, update **both** files together (same servers, different
placeholders).

**Worktrees.** Claude Code starts these servers once, from the *main*
checkout, even when the session works in a linked git worktree
(`CLAUDE_PROJECT_DIR` and cwd both point at the main checkout), so a fixed
root would answer from the wrong tree. `mcp_nav_shared.workspace.WorkspaceSelector`
therefore picks the workspace **per request**, in this order:

1. `CODENAV_MCP_WORKSPACE` / `WEBNAV_MCP_WORKSPACE` set → pinned, never
   overridden (what Cursor's `${workspaceFolder}` wants; `.mcp.json`
   deliberately leaves them unset).
2. The client's MCP roots (`roots/list`): the first one that is the base
   checkout or another worktree of the **same git repository** (compared via
   `git rev-parse --git-common-dir`; roots from unrelated projects are
   ignored).
3. `CLAUDE_PROJECT_DIR`, else the process cwd.

When the chosen root changes, the server stops its language server(s),
drops the caches and re-derives everything relative to the root
(`CODENAV_MCP_SOURCE_ROOT`, `WEBNAV_MCP_ROOTS`, `WEBNAV_MCP_EXCLUDE`). The
`workspace` tool of each server reports the active root and which rule chose
it — call it first when results look like they come from the wrong tree.
Limits: needs a client that answers `roots/list` (handshake-era MCP; the
2026-07-28 revision deprecates roots and forbids server-initiated requests,
in which case rule 3 applies); a tool call already running while the
workspace switches can fail once and succeed on retry.

Both servers are written to be reusable outside this repo (they may ship as
standalone tools for other projects some day), so every SpaceMaker-specific
assumption is pushed into **this repo's own `.mcp.json`/`.cursor/mcp.json`
env vars**, not hardcoded in the server source — following the same
override-with-sane-default shape as `CODENAV_MCP_WORKSPACE`/
`WEBNAV_MCP_WORKSPACE` above:

| Env var | Server | Default (generic) | This repo's value |
|---|---|---|---|
| `CODENAV_MCP_SOURCE_ROOT` | codenav | the whole workspace | `src` (scopes/speeds up `implementations`' class scan and import-path derivation) |
| `CODENAV_MCP_EXTRA_SOURCE_ROOTS` | codenav | none | `tests` (`implementations` also scans these — test doubles such as `FakeFileSystem` — and lists them under a separate heading; their import paths are derived from the workspace root) |
| `WEBNAV_MCP_EXCLUDE` | webnav | nothing treated as generated | `src/spacemaker/adapters/inbound/web/static/js` (the JS `tsc` emits from `web/src/*.ts`: never eagerly opened, dropped from `search_symbol`, rejected by position tools — navigation targets the TS sources only; the CSS/selector index still reads it) |
| `WEBNAV_MCP_ROOTS` | webnav | one unnamed root spanning the whole workspace | `web=web/src,static=src/spacemaker/adapters/inbound/web/static,wireframes=wireframes` (TS sources, production assets, UX wireframes) |

A project that unsets these gets a working, if less scoped/labeled, default
rather than an error or a SpaceMaker-shaped assumption.

## Package layout (separate repos)

The servers were extracted from this repo (2026-09-30) into their own
repositories under `~/Projects/Python/MCPs/`, one per PyPI distribution:

- [`mcp-nav-shared`](https://github.com/illescasDaniel/mcp-nav-shared): import name `mcp_nav_shared`. No
  runtime deps; shared LSP client, symbol resolution, formatting, and
  workspace-root discovery.
- [`codenav-mcp`](https://github.com/illescasDaniel/codenav-mcp): import name `codenav_mcp`. Depends on
  `mcp-nav-shared>=X.Y.0,<X.(Y+1)` from PyPI.
- [`webnav-mcp`](https://github.com/illescasDaniel/webnav-mcp): import name `webnav_mcp`. Same dependency.

SpaceMaker consumes the **published** `codenav-mcp` through `uvx` (no dependency in
`pyproject.toml`, no workspace, no `tool.uv.sources`); `.mcp.json`/`.cursor/mcp.json` pin
the range `>=0.2.0,<0.3`. `ty` (bundled with `codenav-mcp`) still reads the project's own
`.venv` to resolve imports. To try an unreleased change, point `--from` at a local checkout
(`uvx --from ~/Projects/Code/MCPs/codenav-mcp codenav-mcp`; it needs `mcp-nav-shared` from
the same family, so use `--with-editable` for it if it is unreleased).

**`webnav` is different:** it is the npm package
[`webnav-ts-mcp`](https://www.npmjs.com/package/webnav-ts-mcp), developed in its own repo
(`~/Projects/Code/Python/MCPs/webnav-ts-mcp`), and both host configs launch the published
version with `npx --yes webnav-ts-mcp@^0.1.1` (the Python `webnav-mcp` dependency was dropped from
`pyproject.toml`). The first start downloads the package and its language servers
(about 180 MB) into npm's cache; later starts reuse it. To try an unreleased change, temporarily point a
config at `node ~/Projects/Code/Python/MCPs/webnav-ts-mcp/bin/launch.mjs`, which installs and builds
the checkout on first start. The package's own checks are `npm run check` in its directory, and
`npm run upload` / `npm run test-package` publish and verify a release.

## Publishing to PyPI

Each repo has the same tooling (modelled on `srxy`): `uploader` dependency
group (twine), `uv run task sync-uploader` once, then
`uv run task upload -- --build-only` (build + `twine check` into `dist/`),
`upload -- --testpypi`, and `test-package -- --testpypi` (install that exact
version into a fresh venv *outside* the repo, then an MCP stdio handshake for
the servers or an import check for `mcp-nav-shared`). Drop `--testpypi` for the
real index. Credentials come from `~/.pypirc`. PyPI stays the primary index in
the TestPyPI check, so a squatted dependency there can't shadow the real one.

- **Order and versioning:** in 0.x any minor may break the shared API, so the
  servers pin `mcp-nav-shared>=X.Y.0,<X.(Y+1)`. A shared change a server needs
  means bumping and publishing `mcp-nav-shared` first, then raising the pin.
- **Metadata:** each wheel ships its `LICENSE` (`license-files`) and a console
  script (`codenav-mcp` / `webnav-mcp`, i.e. `server:main`), so end users run
  `uvx codenav-mcp`. The READMEs become the PyPI pages, so they use absolute
  links only (relative links 404 on PyPI).
- **Why the fresh-venv check matters:** in-repo runs hide environment bugs;
  codenav once only worked because SpaceMaker's own `.venv/bin/ty` was found
  first.
- **Re-runs:** an index never accepts the same version twice. Bump the
  version, or pass `--skip-existing` after a partial upload.

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

`codenav-mcp` wraps `ty server` (Astral's type checker running
as a language server) as MCP tools. It's named `codenav`, not `ty`, since
`ty` is Astral's name for the underlying tool it wraps, not this project's
server.

**Start with the intent-level tools, drop to position tools for specifics.**
The LSP mirrors position-based lookups 1:1, which forces an agent to
`search_symbol`, work out a tab-aware column, then call `hover`/`definition`/
`references` separately just to answer "what does this do" or "who calls
this". Four composite tools answer those questions in one call, all
name-based (no column arithmetic) via the shared `resolve_symbol()` helper
in `mcp-nav-shared/src/mcp_nav_shared/resolve.py`:

- **`symbol_info(name, file_path=None, include_references=True)`** — the
  default first call for "what is this": header, hover text (signature +
  docstring), definition snippet, and references grouped by file with a
  total count.
- **`outline(file_path)`** — an indented tree of classes/methods/functions
  with line numbers, so an agent can navigate a large file (e.g.
  `src/spacemaker/bootstrap/services/jobs.py`) without reading it end to end.
- **`callers(name, file_path=None)`** — `prepareCallHierarchy` +
  `incomingCalls`: who actually calls this function, with call-site lines.
  Answers "who calls this?" more precisely than `references`, which also
  matches imports and type annotations.
- **`implementations(port_name)`** — see **Protocol conformance** below.

`resolve_symbol()` accepts a dotted `Class.method` query, narrows by
`file_path` when a name is ambiguous, and raises a `SymbolResolutionError`
(a `ToolInputError`) listing candidates rather than guessing when several
symbols share a name. When `Class` doesn't declare `method` itself, the
lookup walks `typeHierarchy/supertypes` breadth-first and resolves the first
base that does — so `AppServices.start_convert` finds `JobsMixin.start_convert`
(`AppServices` is composed from mixins, and it's the type call sites see).

`hover`/`definition`/`references`/`search_symbol`/`diagnostics` (the
original position-based tools) are still useful once a composite tool has
narrowed things down to a specific position. `search_symbol` takes optional
`kind` (SymbolKind labels, comma-separated: `class`, `function,method`) and
`path` (workspace-relative prefix such as `src/`, or a glob) filters, and
ranks production code before tests within a match tier. When some names
actually contain the query, fuzzy-only hits (names that merely contain its
letters in order) are hidden behind a one-line count; `fuzzy=true` lists them.

### `documentSymbol` shape: hierarchical vs flat

`outline` and `resolve_symbol`'s dotted-member lookup both consume
`textDocument/documentSymbol`, whose response shape is capability-negotiated
and not guaranteed: ty may return hierarchical `DocumentSymbol` nodes
(`range`/`selectionRange`/`children`) or flat `SymbolInformation` entries
(`location` only, no nesting), depending on what the client advertised at
`initialize`. `mcp-nav-shared/src/mcp_nav_shared/lsp_client.py` advertises
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

1. **Candidates**: classes under `SOURCE_ROOT` (see below) whose members —
   methods/properties/fields from `documentSymbol`, plus class-body and
   `self.x` attributes and anything inherited from same-workspace base
   classes (matched by simple name, via `ast`) — are a superset of the
   Protocol's own members (`file_path` disambiguates the port) — excluding the port itself (same file + name) and any
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

`implementations` is cached at three levels, each keyed so a hit is always
correct: `LspClient.document_symbol` per document version (bumped by
`ensure_open` exactly when mtime/size change); `_cached_class_infos` per
`(path, mtime_ns, size)` (parsing every file's AST was ~70% of the warm cost);
and the per-candidate `ty` probe verdicts, which can depend on transitive
imports and are therefore dropped wholesale whenever *any* file under
`CODENAV_MCP_SOURCE_ROOT` changes. Warm calls on this repo: ~140 ms → ~15-27 ms.
The probe cache's signature also covers `pyproject.toml`, `uv.lock` and the
venv's `site-packages` mtime, so `uv sync` (`task sync-dev`) invalidates it
automatically — no file watcher or restart hook needed, since every call
re-stats these anyway.

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
directly over LSP. Run it standalone for manual testing with `uvx codenav-mcp`; point it at a different workspace via
the `CODENAV_MCP_WORKSPACE` env var (otherwise falls back as above).

The generic JSON-RPC/LSP wire protocol (subprocess framing, request/
response dispatch, document sync) lives in
`mcp-nav-shared/src/mcp_nav_shared/lsp_client.py` as `LspClient`, shared with
`webnav` below. Only the `ty`-specific launch command
(`codenav-mcp/src/codenav_mcp/ty_command.py`: the workspace's
`.venv` ty, then the `ty` installed with codenav via `ty.find_ty_bin()`, then
`PATH`, then `uvx ty server`) and languageId are codenav's own. If a language
server dies, the tool error quotes its last stderr lines. Location formatting (`path:line:col` headers + snippets)
lives in `mcp-nav-shared/src/mcp_nav_shared/format.py`.

`references` (both servers) uses `format_references()`: at or under
`DEFAULT_REFERENCES_SNIPPET_LIMIT` (8) hits, each gets its own
`path:line:col` header and a short source snippet, same as `definition`.
Above that threshold — a widely-used symbol can have dozens of call sites —
it switches to a compact, file-grouped list with a `(compact list: N > 8
hits)` header and `L<line>:<col>` entries per file instead of full snippets,
so a single broad query doesn't flood the response; the line:col pairs are
still enough to follow up with a targeted `definition`/`hover` call.

### Freshness: `LspClient.refresh()`

A language server only knows what its client tells it. `didOpen` freezes a
document at the text it was opened with, and files created, edited or deleted
behind the server's back (the agent's own Edit tool, `git checkout`, a
formatter) are invisible to workspace-wide answers (`callers`, `references`,
`search_symbol`) — before this existed, `callers` kept reporting call sites
in code that had been reverted, and never saw new ones.
`LspClient.refresh()` (`mcp_nav_shared/lsp_client.py`) therefore runs before
every tool call (`get_client()` in codenav, `_get_client()` in webnav):

1. every open document is re-`stat`ed: changed → `didChange`, missing → `didClose`
   (and its diagnostics/symbol caches are dropped);
2. a `(mtime_ns, size)` snapshot of every file with a watched suffix under the
   workspace (`watch_suffixes`, minus `EXCLUDED_DIR_NAMES` and `watch_ignore`,
   e.g. webnav's generated JS) is diffed against the previous call, and the
   differences go out as `workspace/didChangeWatchedFiles`;
3. webnav's TS client also sets `open_watched_changes=True`: created/changed
   files are additionally `didOpen`ed, because tsserver only treats opened
   documents as part of the project deterministically (its own disk watchers
   are racy right after a write). ty needs only step 2.

Cost: one stat walk per call (~2 ms on this repo). The walk resolves the root
once rather than every file, and skips nested checkouts (any directory below
the root holding a `.git` entry, e.g. worktrees under `.claude/worktrees/`):
walking those used to cost ~15 ms per worktree and reported another
checkout's files to the server. `codenav_mcp/tests/test_ty_live.py` exercises
create/edit/delete against a real `ty`.

**Config changes restart the language server.** ty and tsserver read their
project config once at startup, so the same walk also stamps every
`LspClient.config_names` file anywhere under the workspace (codenav:
`pyproject.toml`, `ty.toml`; webnav's TS server: `tsconfig.json`,
`jsconfig.json`, `package.json`). When one changes, `refresh()` calls
`LspClient.restart()` (stop, start, forget all documents) and runs
`on_restart` (webnav re-opens the JS project; codenav drops its probe
verdicts) instead of reporting file changes, since the fresh server reads the
disk itself. The next result carries `[codenav] restarted the language server
because pyproject.toml changed`. Cost: one cold start (~0.4 s ty, ~1.3 s
tsserver), only right after such an edit. Only a change in file *content* counts (hashed), so a `touch` or a
checkout rewriting identical text doesn't restart; in-flight requests on the old server fail immediately. The
stale-code check is throttled to one stat walk per 2 s. codenav `hover` enrichment skips builtins (typeshed) and
never turns a good hover into an error if the extra `typeDefinition` request fails.

### Notices on tool results

`mcp_nav_shared/notices.py`: every tool is wrapped in `@_notices.tool` (below
`@mcp.tool()`) and appends `[server] …` lines to its text result. One-shot
notices (the restart above) are shown once; a sticky one appears on every call
while the server's own `*.py` files (its package and `mcp_nav_shared`) differ
from what it started with: a stdio server can't reload itself (the client
handshakes once and importlib reloads break shared state), so the fix for
"my MCP fixes aren't live" is a visible *restart the MCP servers* line rather
than a silent old-code answer.

### Bad positions and thin hovers

`LspClient.hover/definition/references/type_definition` validate the position
against the file first and raise `InvalidPositionError` (line out of range,
column beyond the line's UTF-16 length; the end-of-line column is valid), so a
typo isn't mistaken for "nothing there". codenav's `hover` also enriches a bare
type name (ty answers a variable with just `AppServices`): it asks
`textDocument/typeDefinition` and appends where the type is defined, its
header line and the first docstring line.

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
exact name → case-insensitive exact → prefix → substring → other fuzzy hits
(the last tier only listed when no other tier matched, or with `fuzzy=true`),
with Property/Field symbols after other kinds within a tier (tsserver reports
every `S.foo = x` assignment as a Property, which otherwise fills the cap).
Identical `(name, kind, file)` hits are then collapsed, and a same-file
`Variable` is dropped when a Function/Class/Interface/Constant/Enum of that
name already exists (tsserver's `export { foo }` twin). Results are capped
(default 50) with a trailing “and N more” note when truncated.
Name-based tools accept `name`/`query` (and `port_name` for `implementations`)
as aliases of each other so a wrong guess yields a soft hint instead of a
pydantic validation wall.
`definition` / `references` headers use the same `path:line:col` form so
agents can copy positions into follow-up calls.

JSON-RPC errors from the language server are surfaced as tool text
(`LSP error on …`) rather than looking like empty “not found” results.
Other expected failures — missing file, non-UTF-8 file, unsupported
extension (webnav), request timeout, language server exited — are also
returned as text (`mcp_nav_shared/errors.py`) instead of the MCP framework's opaque
“Error executing tool”. If the language server process dies, in-flight
requests fail immediately and the next tool call starts a fresh one.

`diagnostics` falls back to the push `publishDiagnostics` cache when pull
diagnostics are unsupported or empty (common for HTML/CSS servers, and always
the case for some older servers with no pull support). In that
push-only case `LspClient.diagnostics` awaits the first `publishDiagnostics`
after the document was last synced (up to `PUSH_DIAGNOSTICS_TIMEOUT`, 5 s)
rather than answering from a stale or empty cache — before this, the first
`diagnostics` call on a freshly edited `.ts`/`.js` file reported "No
diagnostics." even for an obvious type error.
All four positional tools reject non-Python files (`.py`/`.pyi` only) up
front with a `ToolInputError` — ty otherwise mis-parses e.g. a `.md` file as
Python and `diagnostics` returns a wall of bogus syntax errors for it.
`diagnostics` (both servers) is capped the same way as `search_symbol`
(`format_diagnostics`, `DEFAULT_DIAGNOSTICS_LIMIT = 200` in
`mcp_nav_shared/format.py`), with a trailing "… and N more" line, so a badly
broken file can't flood the caller either.

## `webnav` MCP server

`webnav` (TypeScript, package `webnav-ts-mcp`) gives the same kind of navigation for the
project's JS/TS/HTML/CSS (`symbol_info`, `outline`, `callers`, `implementations`, `search_symbol`,
`definition`, `references`, `hover`, `diagnostics`), multiplexing three
Node-based language servers behind one MCP tool set, routed by file
extension:

- `.ts`/`.tsx`/`.js`/`.jsx`/`.mjs`/`.cjs` → TypeScript 7 native LSP via
  `tsc --lsp --stdio` (shell sources in
  `web/src/` via strict `web/tsconfig.json`; the emitted `static/js/*.js` is
  build output and is excluded from navigation via `WEBNAV_MCP_EXCLUDE`)
- `.html` → `vscode-html-language-server`
- `.css` → `vscode-css-language-server`

HTML/CSS binaries come from `vscode-langservers-extracted`. Both language
servers are ordinary npm dependencies of the webnav package, so nothing is downloaded at runtime and there is no `npx`
fallback. `langCommand.ts` resolves them in order: a TypeScript ≥ 7 (or the
HTML/CSS package) in the navigated workspace's `node_modules` → the copy installed
with webnav. They are launched as `node <server>.js` rather than through `.bin`
shims, so Windows `.cmd` handling and `PATH` differences don't apply.

**Gotcha:** TypeScript 7 no longer ships classic `tsserver.js`. webnav must
launch the native binary (`tsc --lsp --stdio`), never
`typescript-language-server`. A workspace still on TypeScript 5/6 is skipped
and webnav uses its own `typescript@7`.

`callers` (call hierarchy) and `implementations` (`textDocument/implementation`)
answer from the type checker, for functions/methods and for interfaces, classes
and abstract/interface methods respectively. TypeScript 7's LSP has **no type
hierarchy** request, so `Class.member` lookups for a *member inherited from a base
class* (`FancyWidget.greet` where `greet` lives on `Base`) read the `extends`/
`implements` clauses from the source and resolve each named base with
`textDocument/definition`, walking across files breadth-first; library bases
(`extends HTMLElement`, `.d.ts`, `node_modules`) are not followed.

`outline` lists top-level declarations in source order and leaves out the
locals, callbacks and object-literal keys inside functions/variables
(`detailed=true` brings them back) — the language server may return siblings
alphabetically with every local, which made the raw tree ~4 KB for a 500-line
file.

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
Run it standalone for manual testing with
`npx webnav-ts-mcp`; point it at a different workspace via
the `WEBNAV_MCP_WORKSPACE` env var (otherwise falls back as above). See
**Positioning** under codenav above — the same column rules apply.

### Workspace-wide CSS var / selector index

The CSS/HTML language servers each see one document at a time, so `var(--x)`
custom-property usages and `#id`/`.class` selectors can't be cross-referenced
across files that way — the most common question for this project's
`--custom-properties` (defined once in `theme.css`, used across every CSS
file, inline `<style>` block and wireframe). `webnav-ts-mcp`'s `src/webIndex.ts` answers this with a **plain TypeScript scanner, not a language
server**: no `@import` resolution, no real CSS parser, regex/brace-stack
grade. It re-walks the roots on every call but reuses each root's parsed index
while its files are unchanged: the cache key is the `(path, mtime_ns, size)`
of every relevant file (`.css`/`.html`/`.js`/`.mjs`/`.cjs`/`.jsx`/`.ts`/`.mts`/`.cts`/`.tsx`), re-stat'd on
every call, so an edit, add, or delete always invalidates it — there is no
stale-answer window. Measured on this repo: `css_var` ~94 ms → ~2 ms,
`selector` ~58 ms → ~1 ms, HTML `diagnostics` ~115 ms → ~11 ms (the rescan,
not the language server, was the cost).

Which roots get indexed, and under what labels, is generic and
project-configurable via `WEBNAV_MCP_ROOTS` (a comma-separated list of
`label=relative/path` pairs), parsed in `webnav.ts` and passed into
`buildWorkspaceIndex(workspaceRoot, roots)`; `webIndex.ts`
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
  `querySelectorAll`/`closest`/`matches` — including TS type arguments such as
  `querySelector<HTMLElement>(…)` — `className` assignment), grouped
  by file with line numbers, per root. A JS/TS string literal exactly equal
  to the bare name, on a line no DOM API above already covers, is reported
  as a `string literal` hit — this is how ids passed to project helpers
  (`onClick("btn-save", …)`, `bindDisclosure(…)`) show up; it also counts
  as a reference for the unreferenced-selector diagnostic. Hits in
  `WEBNAV_MCP_EXCLUDE` output are labeled `[generated]`.
- **`references`/`definition` fallback**: when the token under the cursor
  in a `.css`/`.html` file is `--name`, `#id` or `.class`, both tools answer
  from this index instead of the single-file language server, limited to the
  root the file lives in (production vs. wireframes define their own values):
  `definition` reports only the definition(s) (a class's CSS rules, an id's
  markup attribute, a variable's declarations), `references` that root's
  definitions and usages; a token with no hits in its own root falls back to
  all roots with a note — this is what
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

## Browser-pane gotchas

- A hidden Browser pane (`document.visibilityState === "hidden"`) doesn't
  render, so CSS transitions/animations never advance and `transitionend`
  fires late — computed values look frozen and the animation seems broken.
  For animation checks, log `document.visibilityState` in the same script;
  if hidden, `tabs_select` the tab and take a `computer` screenshot (which
  makes it visible), then re-run.

## Windows / tooling gotchas

- An earlier `docs/architecture.md` (lowercase) collided case-insensitively
  with `docs/ARCHITECTURE.md` on this Windows filesystem and briefly
  overwrote it — recovered from git history and merged. Watch for this with
  any new doc filename differing only by case.
- `npx` installs the package on first start, which
  brings its own TypeScript 7 and `vscode-*-language-server`. The TypeScript
  port launches servers with `node`, so Windows shims are not involved, but it
  has only been exercised on Linux + Node 22/24 so far.
