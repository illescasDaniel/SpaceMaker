_Last updated: 2026-09-29 (MCP trial package committed, branch `main`)_

## Branch

`main` (up to date with `origin/main` before this commit).

## Current focus

MCP trial follow-ups done and live-verified after Cursor restart: param aliases, webnav `symbol_info`/`outline`, quieter `search_symbol`, `resolve_symbol` drops export-list Variables, READMEs refreshed.

## Next steps

- Trial `code-grader` on the next real SDD feature.
- Exercise the `npm ci` fallback in `copy-venv.sh` next time a branch changes `package-lock.json`.
- Real-app check of the gallery delete animation on the user's library.
- Older open items in `progress.md` (ADB Browse slowness; Easy mode import; native pywebview hardware smoke).

## Just changed

- `mcp_nav_shared.params.resolve_name_query` + aliases on all name-based tools.
- webnav `symbol_info` / `outline`; `filter_workspace_symbols` (Property dedupe + Variable-vs-declaration); same filter in `resolve_symbol`.
- codenav/webnav READMEs (full tool tables; dropped “named not ty” note).
- Live verify after Cursor restart: aliases, outline, quieter gallery search, `symbol_info("renderGalleryItemStage")` → Function.
- Friction entries for this trial marked fixed.
