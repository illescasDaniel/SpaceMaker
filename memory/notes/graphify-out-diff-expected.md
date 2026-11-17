---
name: graphify-out-diff-expected
description: graphify-out always one commit behind after a commit; expected
type: gotcha
date: 2026-09-24
status: superseded
supersedes:
superseded_by: graphify-removed-codenav-renamed
source:
---

`graphify-out/graph.json` / `GRAPH_REPORT.md` will always show an unstaged diff right after a commit — expected, not a bug.

- **Context:** After committing GraphRAG tooling (see the entry below), `git status` showed `graphify-out/graph.json` (later `GRAPH_REPORT.md`) as modified immediately post-commit, on both occasions. Investigated via file mtime vs. commit timestamp rather than assuming it would go away.
- **Finding:** `.githooks/pre-commit` runs *before* Git creates the new commit object, so `git rev-parse HEAD` inside the hook can only ever see the **parent** commit — the new commit's hash doesn't exist yet (it's derived from the tree, so a tracked file can never embed its own containing commit's hash; that's a hash-cycle, not a missing feature). Graphify's `built_at_commit` field therefore always lands one commit behind in what actually gets committed. Separately, Graphify's clustering step re-touches the file a few seconds *after* the hook's `git add` (confirmed via mtime: file changed ~3s after the commit timestamp), re-stamping it with `HEAD` as of that moment — which by then is the *new* commit, since the ref already advanced. That second, unstaged write is the actual diff `git status` shows.
- **Decision:** Documented instead of "fixed" — there is nothing to fix. Re-running the hook or re-committing does not resolve it; it reproduces the identical one-commit-behind drift on the *next* commit. Don't spend time chasing this again.
- **Rationale:** Any tool that stamps a generated artifact with "the commit that produced me" has this same inherent limitation. Silently accepting a permanently-slightly-dirty `git status` after touching graph files is less confusing than a future session assuming it's a regression and trying to patch it.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-24 — `graphify-out/graph.json` / `GRAPH_REPORT.md` will always show an unstaged diff right after a commit — expected, not a bug".

Superseded by [graphify-removed-codenav-renamed](graphify-removed-codenav-renamed.md).
