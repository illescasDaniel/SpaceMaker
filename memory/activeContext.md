_Last updated: 2026-09-24_

## Branch

`main`

## Current focus

Fixed three Windows-only desktop/server bugs found while dogfooding
`uv run task spacemaker`:
1. Chromium/Qt-WebEngine GPU-compositor freeze (web content surface goes
   black/frozen until the window is moved/resized) — **user-confirmed fixed** by
   `QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu-compositing` (win32-only, two prior
   attempts — `--use-angle=d3d9`, `QSG_RHI_BACKEND=opengl` — ruled out, see
   `decisions.md`).
2. Noisy-but-harmless `ConnectionResetError` tracebacks from asyncio's
   `ProactorEventLoop` — fixed by pointing uvicorn's `loop=` at
   `"asyncio:SelectorEventLoop"` directly (`bootstrap/event_loop.py`). **First attempt
   at this broke the app outright** (pointed the string at a wrapper function instead
   of the class directly — uvicorn's custom-loop-string path doesn't unwrap a factory
   function the way its built-in named loops do); reproduced locally, root-caused,
   fixed, and **verified against a new real-process smoke test** before telling the
   user to retest. Full root cause in `decisions.md`.
3. Non-native-looking pywebview dialogs — `qt_native_style.py` (Windows `windows11`
   QStyle, Linux Fusion, macOS left native). Visual confirmation from the user still
   pending (not yet reported either way).

Also added `tests/integration/test_server_smoke.py` (+ `uv run task smoke`) per the
user's explicit request after bug 2's first attempt broke startup silently past every
existing test (all of which use FastAPI's in-process `TestClient`, never a real
`uvicorn.run()`). It boots the actual `python -m spacemaker --server-only` process and
polls a real endpoint, dumping the full subprocess output on failure. Runs automatically
as part of `tests/integration` (`uv run task checks`).

The `QDxgiVSyncService`/`QThreadStorage` shutdown warnings **still occur** after the
freeze fix (user-confirmed via retest) — investigated and closed as a known,
benign/cosmetic Qt WebEngine shutdown-timing quirk (async DXGI teardown racing
`desktop.py`'s `os._exit(0)`), confirmed unrelated to (not fixed by)
`--disable-gpu-compositing`. Decision to stop chasing it recorded in `decisions.md`;
not reopening unless it becomes more than log noise (a hang, crash, non-zero exit).

## Next steps (this thread)

1. Get the user's confirmation that (a) the ConnectionResetError is gone and (b) the
   `windows11`/Fusion `QStyle` is visually applied (close-confirmation `QMessageBox`,
   folder picker) — neither explicitly confirmed yet, only the WebEngine freeze fix has
   been.
2. This session's changes are about to be committed via `/save-changes`.

---

Adopted Graphify's `diagnose multigraph` and `save-result`/`reflect`
feedback loop (documented in `AGENTS.md`, committed `b022d49`), then mirrored
`.cursor/rules/*.mdc` into Claude Code's new `.claude/rules/` directory.
Symlinks (both a blind directory link and per-file `.md`-renamed links)
didn't load in this environment — replaced with five hand-maintained native
`.md` copies, confirmed loading via the user's own `/context` → **Memory
files**. `AGENTS.md` now documents the dual-maintenance requirement (edit
both `.cursor/rules/<name>.mdc` and `.claude/rules/<name>.md` together). See
`decisions.md` for the full symlink-vs-native-copy investigation. This
session's memory-bank/AGENTS.md changes are not yet committed — that's the
immediate next step.

Before that: applied the `claude/graphrag-mkdocs-codebase-graph-891193`
worktree onto `main` via `/apply-worktree`: agent-facing GraphRAG tooling — an
MkDocs knowledge base (`docs/`) and a codebase dependency graph via the
official **Graphify** tool (`graphifyy` on PyPI; CLI is `graphify`), wired
into a version-controlled `.githooks/pre-commit` so the graph stays synced
with every commit on both Windows and Linux. Dev-tooling, not a product
feature, so it didn't go through the Phase Gate Protocol
(wireframe/spec/architecture) — see `progress.md`.

Immediately before that, on `main` itself: the `.claude/skills` symlink was
repointed to a relative target (`../.cursor/skills`) for cross-machine
portability (commit `87b2196`) — see `decisions.md` for the `New-Item`
directory-symlink pitfall discovered along the way.

## Just changed

- `.claude/rules/{agent-memory,graphrag-tools,hexagonal-python,playbooks,sdd}.md` — new, native-format copies of the matching `.cursor/rules/*.mdc` files (no frontmatter — always loaded, same effect as `alwaysApply: true`).
- `AGENTS.md` — added "Rules — Cursor vs Claude Code" section (dual-maintenance requirement, why symlinks were rejected); documented `graphify diagnose multigraph` (trigger-based, not routine) and the `save-result`/`reflect` query-outcome feedback loop, plus that `LESSONS.md` and `memory/decisions.md` are complementary, not redundant.
- `.gitignore` — un-ignored `graphify-out/memory/*.md` and `graphify-out/reflections/LESSONS.md` so the feedback loop persists across sessions/branches instead of resetting per clone.
- `mkdocs.yml`, `docs/index.md`, `docs/testing.md` — MkDocs site (material theme); nav is Home → Architecture → Testing. (`docs/database.md` was added then removed the same session — SpaceMaker has no database.)
- `docs/ARCHITECTURE.md` — merged in an entry-point/routing/persistence analysis, a "Developer setup" section (`git config core.hooksPath .githooks`), and a note on the expected always-one-commit-behind `built_at_commit` drift.
- `.githooks/pre-commit`, `.gitattributes`, `git config core.hooksPath .githooks` (**run this once per clone/worktree** — see README "Setup and run") — hook regenerates `graphify-out/graph.json` + `graphify-out/GRAPH_REPORT.md` (`graphify extract . --code-only` then `graphify cluster-only . --no-label --no-viz`), waits for the write to settle (Windows AV-scanning I/O lag), and only stages them when the diff is more than the commit-stamp/report-line noise — otherwise restores the committed version so `git status` stays clean.
- `pyproject.toml` / `uv.lock` — added `mkdocs`, `mkdocs-material`, `graphifyy` to the `dev` dependency group; new taskipy tasks `docs-serve`, `docs-build`, `graph-update`, `graph-explain`, `graph-path`, `graph-query`.
- `.cursor/rules/graphrag-tools.mdc` — always-on pointer to `AGENTS.md`'s "Codebase knowledge tools" section.
- `CLAUDE.md` deleted; its content merged into `AGENTS.md`, since this repo is also driven from Cursor and other agents that don't read `CLAUDE.md`.
- README.md — documents `git config core.hooksPath .githooks` as required setup, plus pointers to the docs site and graph CLI tasks.
- A custom `ast`-based `scripts/agent_tools/generate_code_graph.py` was built, tested, then deleted in favor of the real Graphify tool once available.

## Gotchas discovered this session

- The task's package name `graphify` doesn't exist on PyPI (404) — the real package is `graphifyy` (double-y); the CLI binary it installs is named `graphify`. Verified via PyPI JSON + the upstream GitHub repo (121k★, YC-backed) before installing.
- `uv run graphify cluster-only . --no-label` (without `--no-viz`) segfaults intermittently on this machine — the `graph.html` visualization step is the likely culprit on Windows + Python 3.14.6. Always pass `--no-viz`.
- No bare `graphify` "build" command and no single-command LLM-free build — the no-API-key pipeline is two steps: `graphify extract <path> --code-only` then `graphify cluster-only <path> --no-label --no-viz`. Default output dir is `graphify-out/`, not the repo root.
- `graphify-out/graph.json` / `GRAPH_REPORT.md` will always drift by exactly one commit's worth of `built_at_commit` right after a commit that has real changes — inherent, not a bug (see `decisions.md`). The pre-commit hook now avoids staging *pure* no-op drift, but a real graph change still legitimately shows the one-behind stamp.
- `cluster-only` can exit before its own label-backfill write has fully settled on disk — the hook polls size/mtime until stable before comparing, rather than trusting the process's exit as "done".
- `uv add` / some `graphify` subprocess calls got denied once each by Claude Code's own auto-mode permission classifier ("Untrusted Code Integration" / "Code from External") — not a hard block, just needed approval or a retry.
- An earlier `docs/architecture.md` (lowercase) collided case-insensitively with `docs/ARCHITECTURE.md` on this Windows filesystem and briefly overwrote it — recovered from git history and merged. Watch for this with any new doc filename differing only by case.

## Next steps

1. `docs/testing.md` is populated for real (BDD given/when/then, mocking standards); no other docs pages are pending.
2. If the `graph.html` crash matters later (interactive visualization), investigate the native dependency behind Graphify's viz step on Python 3.14/Windows, or pin an older Python for that step.
3. Not enabled yet, noted as a future option in `AGENTS.md`: `graphify extract` can index `docs/` (and PDFs) into the same graph via an LLM backend — revisit once the docs corpus is large enough that plain file reads stop being sufficient.
4. When editing any of the five always-on rules, remember to update **both** `.cursor/rules/<name>.mdc` and `.claude/rules/<name>.md` — no automation keeps them in sync, per `AGENTS.md` "Rules — Cursor vs Claude Code".

## Run

```bash
uv run task spacemaker
uv run task docs-serve              # docs site at http://127.0.0.1:8000/ (humans; agents read docs/*.md directly)
uv run task graph-explain "<symbol>" # or: graph-path "<a>" "<b>", graph-query "<question>"
uv run task checks                  # ruff + ty + pytest, works natively on Windows
```

## Notes for Claude Code specifically (this machine)

- Project skills live at `.cursor/skills/` (Cursor's convention); Claude Code only auto-discovers `.claude/skills/`. Fixed via a real OS symlink `.claude/skills -> ../.cursor/skills` (relative target, portable across machines/OS). `git checkout` recreates it correctly on any clone. To recreate manually on Windows, use `cmd /c "mklink /D skills ..\.cursor\skills"` from inside `.claude/` — not `New-Item -ItemType SymbolicLink`, which can mistype it as a file symlink (untraversable by `cd`/Explorer) even for a valid directory target.
- No `.claude/skills`-style fallback is needed for instructions files: Claude Code already reads `AGENTS.md` directly when there's no `CLAUDE.md` (confirmed by direct testing) — which is now moot anyway since `CLAUDE.md` was deleted and merged into `AGENTS.md` this session.
