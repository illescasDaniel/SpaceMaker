# TEMPORARY — codenav write-tools trial log

Scratch log of every interaction (good or bad) with the new `codenav` / `mcp-nav-shared` **write tools** (branches `claude/write-tools` in `~/Projects/Code/MCPs/{codenav-mcp,mcp-nav-shared}`), gathered while implementing a real SDD feature (gallery multi-select + bulk Delete). Delete this file (and revert `.mcp.json`) when the trial ends; fold findings into the MCP repos / `memory/friction/`.

## Setup (temporary, must be reverted)

- `.mcp.json` `codenav` entry now runs `uv run --no-project --with-editable <codenav-mcp> --with-editable <mcp-nav-shared> python -m codenav_mcp.server` (absolute local paths). Revert with `git checkout .mcp.json` once published versions exist.
- Why `--no-project`/two editables: `uv run --directory codenav-mcp --with-editable shared` fails to resolve (codenav-mcp pins `mcp-nav-shared>=0.2.0,<0.3`; PyPI only has 0.1.1).
- `webnav` untouched (its write tools don't exist yet / not on a write branch).
- Tools exposed locally: apply_edit, check_edit, verify_changes, undo_edit, rename_symbol, replace_symbol, insert_symbol, safe_delete, quick_fix, change_signature, move_symbol, move_module (+ the read tools).

## Log

Format: `- [good|bad|neutral] tool(args summary) → what happened / expectation vs. result`

- [neutral] setup: `list_tools()` on the local build returns all 22 tools; dependency resolution only works with the `--no-project` double-editable form above.

### Smoke test (2026-10-03, throwaway `trial_scratch/` package, since deleted)

All 12 write tools connected and worked after the MCP restart (`workspace` → SpaceMaker, source `$CLAUDE_PROJECT_DIR`).

- [good] rename_symbol(name="greet", file_path) preview → diff across 2 files, id; `apply_edit(id)` wrote it, reported "no errors in the edited files" + undo id.
- [good] check_edit(old_string→new_string) → flagged `invalid-return-type` as a *new* error without writing; exactly the intended dry-run.
- [good] safe_delete(apply=false) preview, then default apply → deleted + import-prune ready; clear diff.
- [good] insert_symbol(after="welcome") → blank lines/tabs matched the file, applied by default.
- [good] change_signature(add=[{name, annotation, default, value}]) → updated def and the call site (`excited=True`) in the other file.
- [good] replace_symbol(name="Box.size") → dotted name resolved, re-indented with tabs.
- [good] move_symbol(name, to_file) → created new file, removed from source; no importer needed fixing here.
- [good] move_module → rewrote paths; helpful note that new package dir `sub/` had no `__init__.py`.
- [good] quick_fix with several candidates → refused to guess, listed options; `choice="qualify os.sep"` then applied and reported the diagnostic as *fixed*.
- [good] rename_symbol(parameter="excited") → renamed keyword at call site too.
- [good] verify_changes → listed changed files and new/fixed diagnostics vs HEAD (picked up untracked new files too).
- [good] undo_edit() latest → restored; undo_edit(id=older) after a later edit touched the same files → refused with "changed since it was applied" (safe).
- [bad/noise] rename_symbol preview "non-Python files" note scans `.claude/worktrees/**` copies of docs (listed a duplicate hit for the same line in a worktree). Idea: skip nested worktrees like the read tools' refresh walk does.
- [bad/minor] change_signature on a new unused param produces an `excited is unused` hint reported as a "new warning" — harmless but noisy when adding a param before wiring it.
- [neutral] Tool-param naming: `check_edit`/`rename_symbol` default `apply=false` while `insert_symbol`/`replace_symbol`/`safe_delete`/`quick_fix` default `apply=true`. Works as documented, but easy to mis-assume; worth keeping descriptions explicit (they are).
- [neutral] Edits via these tools are not affected by the Phase Gate hooks, so remember the gate is a process rule: do not use them on `src/` before approvals.

## Round 1 fixes (2026-10-03, uncommitted in the MCP repos) — to re-verify after restart

- rename note scanning `.claude/worktrees/**` → `mentions._text_files` now skips any nested directory holding a `.git` entry (checkouts/linked worktrees), same rule as `iter_python_files`. Unit test `tests/test_mentions.py`. Verify: rename preview on a symbol mentioned in `docs/agent-tooling.md` lists it once, no worktree path.
- "new warning" for an unused added parameter → `simulate.diagnostics_delta` drops hint-severity (4) diagnostics on both sides (`HINT_SEVERITY` in `mcp_nav_shared.diagnostics_delta`). Assertion added to `test_refactor_live.py` (live tests skip without the repo `.venv` ty, so unverified until MCP retry). Verify: change_signature add of an unused param → no hint line.
- inconsistent `apply` defaults → kept (single-symbol edits write, multi-file/dry-run tools preview) but every description's first line now says `[WRITES by default]` or `[PREVIEW by default; apply=true writes]`. Verify: tool list descriptions.
- [neutral] MCP unit suite passes (101) with `uv run --no-project --with-editable . --with-editable ../mcp-nav-shared --with pytest --with pytest-timeout python -m pytest`; plain `uv run pytest` in codenav-mcp cannot resolve (needs shared 0.2.0, unpublished). 80 live tests skip outside the repo `.venv` that has `ty`.

## Round 2 — tool consolidation (2026-10-03, uncommitted in codenav-mcp), requested by the owner

Reason: overlapping tools (check_edit vs replace_symbol/insert_symbol, move_symbol vs move_module…) make an agent hesitate about which to pick. Registered write tools go **12 → 9**:

| New | Replaces | Selector |
|-----|----------|----------|
| `edit` | `check_edit` | text: `old_string`/`new_string` or `new_text` |
| `edit_symbol` | `replace_symbol`, `insert_symbol`, `safe_delete` | `action="replace"\|"insert"\|"delete"`, `name`, `source`, `position` (after/before/into/end), `force` |
| `move` | `move_symbol`, `move_module` | `name` given → symbol, omitted → whole module `file_path` |
| kept | `rename_symbol`, `change_signature`, `quick_fix`, `verify_changes`, `apply_edit`, `undo_edit` | |

- Uniform rule on every write tool: `apply=true` default, `max_new_errors=0` default; blocked edit → preview id for `apply_edit`; `apply=false` always previews. (Replaces the earlier per-tool mix of preview/write defaults and the `[WRITES]/[PREVIEW]` tags.)
- Parameters that an action ignores are rejected with a message instead of swallowed (`edit_symbol(action="delete", source=...)` → error).
- Old implementations kept as private `_edit_text`, `_replace_symbol`, `_insert_symbol`, `_safe_delete`, `_move_symbol`, `_move_module`; `edit_tools.py` is the new front. Old names are no longer registered (test asserts they are absent).
- Tests: 188 pass (incl. live ty). Pre-existing, environment-only, NOT caused by this: `test_ty_live::..._callers_then_answers_track_the_disk` (local ty lacks `prepareCallHierarchy`) and `test_write_edge_live::..._concurrent_calls...` hangs on the untouched baseline too. Live tests only run with `.venv/bin/ty` in the repo; I symlinked the uv tool's ty there (git-ignored).
- To verify after restart: tool list shows 9 write tools with the new names; try edit/edit_symbol/move on real SpaceMaker code during the feature.
