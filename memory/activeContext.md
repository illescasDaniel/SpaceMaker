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

Separately, ran a "lean agent context" pass (user-requested, see `decisions.md`):
`AGENTS.md` is now the sole always-on instructions file for both Cursor and Claude
Code; the four rule pairs that repeated it (`agent-memory`, `sdd`, `playbooks`,
`graphrag-tools`) were deleted from `.cursor/rules/` and `.claude/rules/`, and their
content merged into `AGENTS.md`, the `agent-memory`/`sdd-feature` skills, or the new
`docs/agent-tooling.md`. Only `hexagonal-python` remains as a rule, now path-scoped to
`src/spacemaker/**`. `tests/unit/test_agent_context.py` enforces that every
`.cursor/rules/*.mdc` has a body- and scoping-identical `.claude/rules/*.md` pair — a
hard requirement from the user, also saved to Claude's cross-session memory. Old
finished history moved to new `memory/archive.md` (not read at session start).

## Next steps (this thread)

1. Get the user's confirmation that (a) the ConnectionResetError is gone and (b) the
   `windows11`/Fusion `QStyle` is visually applied (close-confirmation `QMessageBox`,
   folder picker) — neither explicitly confirmed yet, only the WebEngine freeze fix has
   been.
2. Windows bug fixes already committed separately (`176db11`, ahead of this
   memory update). `uv run task checks` and `uv run task docs-build` both verified
   clean for the agent-context refactor; that refactor is being committed now via
   `/save-changes`.

## Run

```bash
uv run task spacemaker
uv run task docs-serve              # docs site at http://127.0.0.1:8000/ (humans; agents read docs/*.md directly)
uv run task graph-explain "<symbol>" # or: graph-path "<a>" "<b>", graph-query "<question>"
uv run task checks                  # ruff + ty + pytest, works natively on Windows
uv run task smoke                   # real-process server smoke test (subset of checks)
```

## Notes for Claude Code specifically (this machine)

- Project skills live at `.cursor/skills/` (Cursor's convention); Claude Code only auto-discovers `.claude/skills/`. Fixed via a real OS symlink `.claude/skills -> ../.cursor/skills` (relative target, portable across machines/OS). `git checkout` recreates it correctly on any clone.
- Older finished threads (Graphify/MkDocs adoption, the `.claude/skills` symlink fix, gotchas): `memory/archive.md` and `docs/agent-tooling.md`.
