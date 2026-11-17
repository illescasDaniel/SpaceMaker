---
name: claude-skills-symlink-relative
description: .claude/skills -> ../.cursor/skills relative; on Windows use mklink /D, not New-Item
type: gotcha
date: 2026-09-24
status: current
supersedes: claude-skills-symlink
superseded_by:
source:
---

`.claude/skills` symlink: relative target, and `New-Item` directory-symlink pitfall.

- **Context:** Following up on the previous session's `.claude/skills` symlink (see the `2026-09-24 — Claude Code project-skill discovery` entry below), the tracked blob content was found to be the literal absolute path `C:/Users/kaumi/Documents/Projects/SpaceMaker/.cursor/skills` — baked to this machine's username and clone location, so it would dangle on any other Windows machine and on Linux/macOS. Separately, recreating the symlink by hand with `New-Item -ItemType SymbolicLink -Path .claude\skills -Target ..\.cursor\skills` produced a **file**-type reparse point (`PSIsContainer: False`, `Attributes: Archive, ReparsePoint`) even though the target is a directory — so native Windows tools (`cd`, Explorer) couldn't traverse it, while Git Bash's `ls`/`cd` (POSIX emulation, ignores the NTFS file/dir reparse subtype) worked fine and masked the bug.
- **Decision:** Repointed the symlink to the relative target `../.cursor/skills` (commit `87b2196`). When the symlink needs manual recreation on Windows, use `mklink /D skills ..\.cursor\skills` (run from inside `.claude/`, via `cmd /c`) — not `New-Item -ItemType SymbolicLink`, which mistyped the reparse point even with a valid, existing directory target. Verified `git checkout` itself always creates the correct `Directory` reparse point (confirmed via a throwaway `git worktree add --detach` at a different path — `PSIsContainer: True`), so this pitfall only affects manual recreation, not clones/checkouts by git or other users.
- **Rationale:** A relative symlink target is required for the link to resolve on any machine/OS; `mklink /D` is the reliable manual-recreation path on Windows since `New-Item`'s directory detection for symlinks is unreliable, at least with relative targets.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-24 — `.claude/skills` symlink: relative target, and `New-Item` directory-symlink pitfall".
