---
name: claude-rules-hand-maintained-copies
description: .claude/rules are hand-maintained copies of .cursor/rules, not symlinks; drift-tested
type: decision
date: 2026-09-24
status: current
supersedes:
superseded_by:
source:
---

`.claude/rules/` mirrors `.cursor/rules/`: hand-maintained copies, not symlinks.

- **Context:** Claude Code shipped a new `.claude/rules/` feature (analogous to Cursor's `.cursor/rules/`). Tried the same symlink pattern already used for `.claude/skills -> ../.cursor/skills` (a directory symlink): first a blind directory symlink (rejected on inspection — Claude Code's docs say discovery is by literal `.md` extension, and every Cursor rule file is `.mdc`), then per-file symlinks named `<name>.md` pointing at the real `<name>.mdc` targets (valid on disk, content read correctly via `cat`/`Read`, but two independent tests — a fresh subagent probing for a phrase unique to one rule file, and the user's own `/context` in a genuinely fresh session — both showed **zero** `.claude/rules/` files loaded, only `AGENTS.md` under **Memory files**). Rewrote as five native `.claude/rules/*.md` files with plain-markdown content (no frontmatter — Claude Code only reads a `paths` field and ignores everything else, so omitting it entirely gives the same "always loaded" behavior as Cursor's `alwaysApply: true`). Re-tested with the user's own `/context`: all five now appear under **Memory files**.
- **Decision:** `.claude/rules/*.md` are hand-maintained duplicates of `.cursor/rules/*.mdc`, not symlinks or generated copies. Documented the dual-maintenance requirement directly in `AGENTS.md` ("Rules — Cursor vs Claude Code" section): edit both copies together, a mismatch is a bug.
- **Rationale:** The symlink approach that worked for `.claude/skills` doesn't generalize to `.claude/rules/` because skills discovery apparently tolerates (or doesn't care about) the underlying file extension the way rules discovery does — or possibly this specific desktop-app session type just doesn't implement `.claude/rules/` symlink-following at all (untested: whether a real standalone `claude` CLI session would resolve the symlink where this environment didn't). Rather than keep guessing at environment-specific symlink behavior, hand-maintained copies are unambiguous, verified working, and the five files are small enough that manual sync isn't a meaningful burden. A follow-up subagent test for the *native* `.md` files (no symlink involved) also came back negative before the user's own fresh-session `/context` confirmed they load — meaning a spawned subagent in this environment does **not** reliably reflect what a genuine new top-level session loads; don't trust subagent self-report for this class of question again, use `/context` in an actual fresh session instead.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-24 — `.claude/rules/` mirrors `.cursor/rules/`: hand-maintained copies, not symlinks".
