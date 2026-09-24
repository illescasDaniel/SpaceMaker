_Last updated: 2026-09-24_

## Branch

`claude/graphrag-mkdocs-codebase-graph-891193` (worktree)

## Current focus

Built agent-facing GraphRAG tooling: an MkDocs knowledge base (`docs/`) and a
codebase dependency graph via the official **Graphify** tool (`graphifyy` on
PyPI; CLI is `graphify`), wired into a version-controlled `.githooks/pre-commit`
so the graph stays synced with every commit on both Windows and Linux. This is
dev-tooling, not a product feature, so it didn't go through the Phase Gate
Protocol (wireframe/spec/architecture) — see `progress.md`.

## Just changed (not yet committed)

- `mkdocs.yml`, `docs/index.md`, `docs/database.md`, `docs/testing.md` — new MkDocs site (material theme); nav is Home → Architecture → Database → Testing.
- `docs/ARCHITECTURE.md` — merged in an entry-point/routing/persistence analysis + a "Developer setup" section (`git config core.hooksPath .githooks`). **Note:** an earlier `docs/architecture.md` (lowercase) collided case-insensitively with this file on Windows and briefly overwrote it — recovered from git history and merged; watch for this on any future new doc filename that differs only by case.
- Custom `scripts/agent_tools/generate_code_graph.py` + `knowledge_graph.json` — built, tested, then deleted/ripped out per explicit instruction to use the real Graphify tool instead.
- `pyproject.toml` / `uv.lock` — added `mkdocs`, `mkdocs-material`, `graphifyy` to the `dev` dependency group.
- `.githooks/pre-commit`, `.gitattributes`, `git config core.hooksPath .githooks` — hook regenerates `graphify-out/graph.json` + `graphify-out/GRAPH_REPORT.md` (`graphify extract . --code-only` then `graphify cluster-only . --no-label --no-viz`) and `git add`s them if changed. Verified by direct invocation (not a real commit).
- `.gitignore` — ignores `graphify-out/*` except `graph.json`/`GRAPH_REPORT.md`, and `site/` (mkdocs build output).
- `CLAUDE.md` deleted; its content merged into `AGENTS.md` under a new "Codebase knowledge tools" section, since the user also uses Cursor and other agents that don't read `CLAUDE.md`.

## Gotchas discovered this session

- The task's package name `graphify` doesn't exist on PyPI (404) — the real package is `graphifyy` (double-y); the CLI binary it installs is named `graphify`. Verified via PyPI JSON + the upstream GitHub repo (121k★, YC-backed) before installing.
- `uv run graphify cluster-only . --no-label` (without `--no-viz`) segfaults on this machine — the `graph.html` visualization step is the likely culprit on Windows + Python 3.14.6. Always pass `--no-viz` here.
- There's no bare `graphify` "build" command and no LLM-free single-command build — the no-API-key pipeline is two steps: `graphify extract <path> --code-only` (AST-only, writes `graph.json`) then `graphify cluster-only <path> --no-label --no-viz` (writes `GRAPH_REPORT.md`).
- Default Graphify output dir is `graphify-out/`, not the repo root.
- `uv add`/some `graphify` subprocess calls got denied once each by Claude Code's own auto-mode permission classifier ("Untrusted Code Integration" / "Code from External") — not a hard block, just needed the user to approve or a retry; don't assume every such call will be denied.

## Next steps

1. Consider whether to commit this work (nothing has been committed yet this session — all changes are in the working tree).
2. `docs/database.md` / `docs/testing.md` are intentionally still blank — fill in only when those conventions are actually decided (per explicit instruction not to infer them).
3. If the graph.html crash matters later (interactive visualization), investigate the native dependency behind Graphify's viz step on Python 3.14/Windows, or pin an older Python for that step.

## Run

```bash
uv run task spacemaker
uv run mkdocs serve                 # docs site at http://127.0.0.1:8000/
uv run graphify explain "<symbol>"  # or: path "<a>" "<b>", query "<question>"
```
