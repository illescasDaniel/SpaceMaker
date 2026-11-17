---
name: graphrag-mkdocs-graphify
description: MkDocs + Graphify for agent navigation; CLAUDE.md merged into AGENTS.md
type: decision
date: 2026-09-24
status: superseded
supersedes:
superseded_by: graphify-removed-codenav-renamed
source:
---

GraphRAG agent tooling: MkDocs + Graphify (not custom AST script), CLAUDE.md merged into AGENTS.md.

- **Context:** Built agent-facing "GraphRAG" tooling so AI agents can orient in this codebase without broad file reads: an MkDocs knowledge base and a structural dependency graph. First pass used a hand-rolled `ast`-based script (`scripts/agent_tools/generate_code_graph.py` → `knowledge_graph.json`); a later instruction said to rip that out and use the official open-source "Graphify" tool instead, with the exact package name `graphify`.
- **Decision:** Verified `graphify` does not exist on PyPI (404) before installing anything — the real, legitimate package (121k★ GitHub repo, YC-backed, matches the described `explain`/`path`/`query` + `graph.json`/`GRAPH_REPORT.md` CLI exactly) is `graphifyy` (double-y; the CLI binary it installs is `graphify`). Installed that instead and flagged the correction. Deleted the custom script/`knowledge_graph.json`. `.githooks/pre-commit` (version-controlled, activated via `git config core.hooksPath .githooks` — see prior symlink-discovery entry on why this repo avoids relying on `.git/hooks/`) now runs `graphify extract . --code-only` then `graphify cluster-only . --no-label --no-viz` (the no-LLM-API-key pipeline; `--no-viz` avoids a native segfault on this Windows/Python-3.14.6 setup) and auto-stages `graphify-out/graph.json` + `graphify-out/GRAPH_REPORT.md` if changed. Separately, merged `CLAUDE.md`'s content into `AGENTS.md` and deleted `CLAUDE.md`, since the user also drives this repo from Cursor and other agents that only read `AGENTS.md`.
- **Rationale:** Installing an unverified/mistyped package name and wiring it into a hook that auto-executes on every future commit on both the user's Windows and Linux machines is a real supply-chain risk surface — worth a PyPI/GitHub legitimacy check before `uv add`, not after. The custom AST script was reasonable as a first pass but strictly worse than the real tool once available (no fully-qualified node IDs, best-effort name-only call matching, no query/path/explain CLI). A single `AGENTS.md` avoids the two-file drift risk that motivated the earlier "did not add a `CLAUDE.md` symlink" non-decision — now there's nothing for it to drift from.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-24 — GraphRAG agent tooling: MkDocs + Graphify (not custom AST script), CLAUDE.md merged into AGENTS.md".

Superseded by [graphify-removed-codenav-renamed](graphify-removed-codenav-renamed.md): Graphify removed; MkDocs and the AGENTS.md merge still hold.
