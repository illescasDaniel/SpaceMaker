# Codebase knowledge tools (MkDocs + Graphify)

Full instructions: `AGENTS.md` → "Codebase knowledge tools (orient before
editing)". This rule is a pointer/reminder, not the source of truth — if it
and `AGENTS.md` ever disagree, `AGENTS.md` wins.

## Before making a non-trivial change

1. Check `docs/` for the *why* — architecture rationale, domain concepts.
   **As an agent, read the `.md` files directly** (`docs/index.md`,
   `docs/ARCHITECTURE.md`, `docs/testing.md`); `uv run task docs-serve` is
   for humans browsing the rendered site, not for you.
2. Check the Graphify knowledge graph for the *what calls what* — do **not**
   read raw `graphify-out/graph.json`:
   ```bash
   uv run task graph-explain "<symbol>"
   uv run task graph-path "<source>" "<target>"
   uv run task graph-query "<question>"
   ```
3. Neither tool skips a Phase Gate (`AGENTS.md`) — they make you faster
   *within* the protocol, not a shortcut around it.

## Keeping the graph in sync

`graphify-out/graph.json` + `graphify-out/GRAPH_REPORT.md` are regenerated
and staged automatically by `.githooks/pre-commit` (active once
`git config core.hooksPath .githooks` has been run once per clone/worktree —
see `docs/ARCHITECTURE.md` "Developer setup"). To regenerate by hand without
committing: `uv run task graph-update`.
