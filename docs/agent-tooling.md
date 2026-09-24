# Agent tooling reference

Reference material for the AI-agent-facing tooling in this repo: advanced
Graphify usage, how the Cursor/Claude Code rule pairs are maintained, and
durable gotchas hit while building this tooling. `AGENTS.md` covers the
everyday commands and rules; this page is for when you need more.

## Graphify: advanced usage

**Fidelity check — `graphify diagnose multigraph`.** Not a per-task step.
Run it only after a big refactor (renames/moves that could confuse the
extractor) or when a `graph-explain`/`graph-path`/`graph-query` result looks
suspicious (missing edges, an unexpected empty answer):

```bash
uv run graphify diagnose multigraph
```

It reports edge collapse/dangling-endpoint risk against
`graphify-out/graph.json`; a clean run is 0 collapsed edges and 0 dangling
endpoints.

**Query feedback loop — `save-result` / `reflect`.** After a
`graph-explain`/`graph-path`/`graph-query` call that actually informed a
real decision (not trivial one-off lookups), tag the outcome:

```bash
uv run graphify save-result --question "<question>" --answer "<short answer>" \
  --type query --nodes "<Symbol1>" "<Symbol2>" --outcome useful|dead_end|corrected
uv run graphify reflect   # regenerates graphify-out/reflections/LESSONS.md
```

This is deterministic bookkeeping, no LLM — `reflect` just aggregates tagged
outcomes into a per-symbol/per-community "how reliable was this" summary.
`graphify-out/memory/*.md` and `graphify-out/reflections/LESSONS.md` are
git-tracked (see `.gitignore`) so the signal accumulates across sessions and
branches instead of resetting per clone.

`LESSONS.md` is **not** a replacement for `memory/decisions.md`: `LESSONS.md`
is auto-generated, per-symbol "was this graph node useful when queried"
signal; `decisions.md` is hand-written, per-decision "why we built it this
way" narrative. They serve different questions and both stay.

**Not enabled yet, possible future option:** `graphify extract` also
supports indexing `docs/` (and PDFs) into the *same* graph via an LLM
backend (`--code-only` is what currently opts us out of that). This would
let `explain`/`path`/`query` connect prose concepts to code symbols
directly. Not worth it yet at this doc corpus's size, and it costs an LLM
API key + tokens + non-determinism — revisit if `docs/` grows enough that
plain file reads stop being sufficient.

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

## Windows / tooling gotchas

- The Graphify package name `graphify` doesn't exist on PyPI (404) — the
  real package is `graphifyy` (double-y); the CLI binary it installs is
  named `graphify`. Verified via PyPI JSON + the upstream GitHub repo before
  installing.
- `uv run graphify cluster-only . --no-label` (without `--no-viz`) segfaults
  intermittently on this machine — the `graph.html` visualization step is
  the likely culprit on Windows + Python 3.14.6. Always pass `--no-viz`.
  Worth an upstream report if the interactive visualization is ever wanted.
- No bare `graphify` "build" command and no single-command LLM-free build —
  the no-API-key pipeline is two steps: `graphify extract <path> --code-only`
  then `graphify cluster-only <path> --no-label --no-viz`. Default output
  dir is `graphify-out/`, not the repo root.
- `graphify-out/graph.json` / `GRAPH_REPORT.md` will always drift by exactly
  one commit's worth of `built_at_commit` right after a commit that has real
  changes — inherent, not a bug. The `.githooks/pre-commit` hook avoids
  staging *pure* no-op drift, but a real graph change still legitimately
  shows the one-behind stamp.
- `cluster-only` can exit before its own label-backfill write has fully
  settled on disk — the pre-commit hook polls size/mtime until stable before
  comparing, rather than trusting the process's exit as "done".
- An earlier `docs/architecture.md` (lowercase) collided case-insensitively
  with `docs/ARCHITECTURE.md` on this Windows filesystem and briefly
  overwrote it — recovered from git history and merged. Watch for this with
  any new doc filename differing only by case.
