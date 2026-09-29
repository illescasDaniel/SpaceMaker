# MCP evaluation — `codenav` & `webnav` (2026-09-29)

**Question:** how useful are these MCPs for AI agentic coding?

**Short answer:** very useful for *reading and understanding* code, and not yet trustworthy right after
*writing* it. The composite tools (`symbol_info`, `callers`, `implementations`, `css_var`, `selector`)
answer in one call, in a few milliseconds, questions that take 3–6 grep/read rounds and still
miss things. Every answer I cross-checked against grep was exact. The one serious gap is
**freshness after on-disk edits**: files the agent (or git) changes are not re-synced unless a tool
touches that exact path. In an edit→verify loop the tools can report ghost or missing call sites
with no warning.

| Server | Overall | Read-only navigation | After edits | Speed (warm) | Maturity |
|---|---|---|---|---|---|
| `codenav` (Python / ty) | **7.5 / 10** | 9 | 4 | 2–25 ms | 7 |
| `webnav` (TS/HTML/CSS) | **7 / 10** | 8 | 6 | 3–70 ms | 7 |

Fixing the freshness bug (shared root cause, one place: `mcp_nav_shared/lsp_client.py`) would take
both servers to about 8.5–9.

---

## Method

- The tests ran in a cloud session on this repo (`feature/mcp-improvements` head `3e42762`), through
  the real MCP connection, as an agent would use it.
- I cross-checked results against `grep`. I ran freshness tests with temporary files and edits, all
  reverted afterwards (`git status` clean).
- Latency: a stdio MCP client (`mcp` SDK) launched each server from scratch and timed 4 calls per
  tool. Cold means the first call; warm means the median of the next 3. The Node language servers
  weren't installed locally (`node_modules/` absent), so webnav used its `npx` fallback. That
  inflates webnav's cold numbers.
- Test suites: `mcp-nav-shared` 107, `codenav_mcp` 26, `webnav_mcp` 96 passing (3 skipped: the TS
  smoke tests need `npm ci`). Each suite takes about 1 s.

## Latency

| Server | Tool | Cold | Warm (median) | Output size |
|---|---|---|---|---|
| codenav | server start (`initialize`) | 761 ms | — | — |
| codenav | `symbol_info` | 388 ms (ty start) | 8 ms | 0.6–1.3 KB |
| codenav | `outline` | 3 ms | 2 ms | 0.9 KB |
| codenav | `callers` | 24 ms | 11 ms | 0.6 KB |
| codenav | `implementations` | **1 829 ms** | 24 ms | 0.2 KB |
| codenav | `search_symbol("convert")` | 13 ms | 7 ms | **5.3 KB** |
| codenav | `diagnostics` | 51 ms | 3 ms | — |
| codenav | `definition` / `references` / `hover` | 5–82 ms | 3–4 ms | 0.3 KB |
| webnav | server start | 892 ms | — | — |
| webnav | `symbol_info` (tsserver start via npx) | 2 981 ms | 69 ms | 1.5 KB |
| webnav | `outline` | 52 ms | 4 ms | **4 KB** |
| webnav | `search_symbol` | 120 ms | 21 ms | 0.3 KB |
| webnav | `css_var` | 302 ms | 5 ms | 1.7 KB |
| webnav | `selector` | 7 ms | 4 ms | 0.9 KB |
| webnav | `diagnostics` .html (HTML server via npx) | 2 524 ms | 13 ms | 0.5 KB |
| webnav | `diagnostics` .css (CSS server via npx) | 1 742 ms | 20 ms | — |
| webnav | `definition` / `references` | 5–10 ms | 4–7 ms | 0.7–1.7 KB |

Speed is not a concern. Warm calls are faster than a single `grep -r`, and the cold costs are paid
once per session. The only cold outliers come from starting a language server
(`implementations`' first probe; webnav's `npx` downloads).

---

## `codenav` — Python via ty — 7.5 / 10

**Strengths**
- Name-based composites, with no column arithmetic. `symbol_info("JobsMixin.start_convert")`
  returns the signature, a definition snippet and grouped references in one call.
  `AppServices.start_convert` resolves through the mixin hierarchy.
- Accuracy matched grep exactly: `FileSystemPort` has 37 refs in 17 files, and grep finds the same
  37/17. `references` to `can_start_convert` returned 11, including tests.
- It resolves through dependency injection: `definition` on `services.start_convert(...)` in a
  FastAPI route jumps to `JobsMixin.start_convert`.
- `callers` is precise. It includes tests and constructor calls (`callers("LocalFileSystem")`) and
  excludes imports and annotations.
- `implementations` answers the key hexagonal-architecture question (which adapters implement this
  Protocol port), and plain LSP can't. The results were right for every port tried
  (`DeviceRepositoryPort` → ADB + AFC, `MediaConverterPort`, `ContentHasher`), and each was
  type-verified by ty. It also refuses clearly on a non-Protocol (`AppServices`) and on a Protocol
  with no implementers (`WebSocketLike`).
- Errors come back as text and are actionable: ambiguous names list their candidates
  (`on_progress` → 5 with paths), and non-Python files and missing files get clear messages.
- `diagnostics` is accurate and fresh for the file you ask about. It caught an `invalid-argument-type`
  and then an `invalid-return-type` after an edit, and correctly accepted a `bool` return as an
  `int`.
- `workspace` explains in plain language which checkout it's navigating.

**Weaknesses**
- 🐞 **Stale after disk edits** (high severity; see
  [friction](../../memory/friction/2026-09-29-codenav-stale-after-disk-edits.md)):
  - New files and edits to files codenav hasn't opened are invisible to
    `callers`/`references`/`search_symbol`.
  - Deleted or reverted code keeps showing up as ghost callers, for example
    `_probe_three … calls at L36` in a file that now has 31 lines.
  - `symbol_info` on a deleted symbol returns "File not found".

  Root cause: the LSP client never sends `didChangeWatchedFiles` or `didClose`.
- `implementations` doesn't see test fakes (`FakeFileSystem`, …) because `SOURCE_ROOT=src`. Those
  fakes are exactly what an agent has to update when a port changes.
- `search_symbol` is noisy on broad queries: 50 hits and 5 KB for "convert", mostly
  `test_given_…` functions, with no kind or path filter.
- `hover` output is thin: on a variable it's just `AppServices`. An out-of-range line returns "No
  hover information" instead of a range error.
- `implementations` cold takes about 1.8 s. That's fine, but worth knowing.

**How to use it:** start with `symbol_info` or `outline`. Then use `callers` before changing a
signature and `implementations` before changing a port. Use `diagnostics` after editing a file, as
a faster ty check. **After editing, call `outline(file_path=…)` on every file you changed before
trusting `callers`/`references`**, until the freshness bug is fixed.

### Per-tool scores

| Tool | Score | Note |
|---|---|---|
| `symbol_info` | 9 | The best first call; mixin-aware dotted lookup |
| `outline` | 9 | Compact, in source order, 2 ms |
| `callers` | 8 | Precise; affected by staleness |
| `implementations` | 8 | Unique value; misses test fakes |
| `diagnostics` | 9 | Accurate, fresh per file, 3 ms |
| `definition` | 8 | Resolves through DI |
| `references` | 8 | A compact list above 8 hits is a good default |
| `hover` | 6 | Thin; silent on bad positions |
| `search_symbol` | 6 | Floods on broad queries; no filters |
| `workspace` | 8 | Clear "why this root" |

---

## `webnav` — TS/HTML/CSS — 7 / 10

**Strengths**
- `css_var` and `selector` answer questions no single-file language server can. Results are split
  per root (`web` / `static` / `wireframes`), definitions show their context
  (`@media (prefers-color-scheme: dark) › :root = #0f1419`), and hits in generated output are
  labeled `[generated]`.
- HTML/CSS `diagnostics` add index-derived dead-CSS warnings. I checked all 7 warnings on
  `wireframes/app.html` (`.ui-mode-toggle`, `.alert-actions`, `.fail`, …) and every one is really
  unreferenced.
- TS `symbol_info` is accurate across files: `apiSend` has 61 refs in 12 files, which matches grep
  once doc comments are excluded. JSDoc is included.
- It handles a missing install gracefully: with no `node_modules`, it falls back to `npx`, logs the
  fact, and keeps working.
- Generated JS is rejected with a pointer back to the TS source.
- New and deleted TS files are picked up correctly, because tsserver watches the disk itself.

**Weaknesses**
- 🐞 **Stale after edits to existing TS files** (see
  [friction](../../memory/friction/2026-09-29-webnav-stale-open-ts-files.md)). All files are opened
  eagerly at startup, and tsserver then ignores the disk for open files. Same root cause as codenav.
- 🐞 **`selector` misses TS generic calls** such as `querySelector<HTMLElement>(".x")`: 6 sites in
  `web/src`, and the regex is at `web_index.py:58`. See
  [friction](../../memory/friction/2026-09-29-selector-misses-ts-generic-querySelector.md).
- `outline` is sorted **alphabetically, not by line**, and lists every local const, object-literal
  key and anonymous callback (4 KB for 520 lines). It's the weakest tool in either server.
- `definition` on a `var(--x)` in CSS returns the full `css_var` dump for *all* roots, including
  wireframes, rather than the definition for the file's own root.
- Cold starts through `npx` take 2–3 s per language server. The cloud environment has no
  `npm ci`, so the TS smoke tests are skipped here.

**How to use it:** use `selector` before renaming or deleting a class or id, and `css_var` before
changing a theme token. Run `diagnostics` on CSS/HTML to find dead rules. Use `symbol_info` for TS
APIs and exported helpers. Prefer reading the file over `outline`.

### Per-tool scores

| Tool | Score | Note |
|---|---|---|
| `css_var` | 9 | Unique, per-root, fast |
| `selector` | 7 | Unique; misses generic `querySelector<T>` |
| `diagnostics` | 8 | Dead-CSS warnings verified correct |
| `symbol_info` | 8 | Accurate across files; affected by staleness |
| `search_symbol` | 8 | Clean, deduped |
| `references` / `definition` | 7 | CSS fallback too verbose |
| `hover` | 8 | Full TS signature + MDN docs |
| `outline` | 5 | Alphabetical, noisy |
| `workspace` | 8 | — |

---

## Stability, robustness and maturity

**Good**
- 229 fast unit tests.
- Every failure mode I tried returns readable text rather than an opaque error: a missing file, a
  wrong extension, an unknown symbol, a non-Protocol port, a selector without `#`/`.`.
- Configuration is env-driven and portable, not specific to this repo.
- The per-request workspace selection handles worktrees.
- The friction log shows an active hardening loop: 10 earlier entries, all fixed.

**Missing**
- No tests cover external edits or deletes. That explains why the freshness bug went unnoticed.
- The TS smoke tests are skipped when `npm ci` hasn't run, as in this environment.
- It's young: all friction entries are from the same day, and it hasn't been used on real feature
  work yet.

## Bugs and improvements found (logged in `memory/friction/`)

| # | Server | Severity | Issue |
|---|---|---|---|
| 1 | codenav | wrong-result | Stale after on-disk create/edit/delete (ghost and missing callers) |
| 2 | webnav | wrong-result | Stale after edits to already-open TS files |
| 3 | webnav | wrong-result | `selector` misses `querySelector<T>(…)` / `closest<T>(…)` |
| 4 | webnav | confusing | `outline` sorted alphabetically and noisy |
| 5 | codenav | missing-feature | `implementations` ignores test fakes |
| 6 | codenav | confusing | `search_symbol` has no kind/path filter; tests dominate |
| 7 | webnav | confusing | CSS `definition` fallback dumps every root |

Recommended order: fix 1 and 2 together (the shared `LspClient` re-stats open files on every call,
resyncs or closes them, and sends `workspace/didChangeWatchedFiles` for changes under the roots),
then fix 3 (a one-line regex change), then 4.

## Verdict

For an AI agent, these MCPs remove the most expensive part of coding in an unfamiliar codebase:
building an accurate picture of who calls what. `implementations`, `css_var` and `selector` have
no good grep equivalent. Everything else answers in milliseconds, with less output than grep and
with type-aware precision. Until bugs 1–2 are fixed, treat their answers as a snapshot taken when
the server last saw each file, and re-`outline` the files you've just edited.
