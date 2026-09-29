---
name: new-worktree
description: >-
  Create an isolated git worktree + branch for a new task, then copy (or
  regenerate) .venv and node_modules from the primary checkout so the
  worktree is immediately usable without re-downloading dependencies. Use
  when the user invokes /new-worktree or asks to start a new worktree/task
  in isolation. Also works from inside an existing worktree (e.g. one the
  Claude desktop app created): it then only populates .venv/node_modules.
disable-model-invocation: true
---

# New Worktree

Use only when the user explicitly invokes `/new-worktree <task description>` (or clearly asks to start
a new isolated worktree for a task), **or** invokes `/new-worktree` from inside an existing non-primary
worktree to get its dependencies (see "Already inside a worktree" below).

## Goal

Two steps: (1) create an isolated git worktree + branch for the task, **always forked from whatever
branch is currently checked out** — never `main`/`origin/main` unless that happens to be the current
branch; (2) populate `.venv` and `node_modules` in it, by copying from the primary checkout and
rewriting the absolute paths baked into `.venv` (fast, no re-downloads) or regenerating via
`uv sync`/`npm ci` when a copy isn't possible — so `uv run task checks` works immediately in the new
worktree.

## Step 1 — create the worktree + branch

Run from the **primary checkout only**. If this session is already inside a non-primary worktree, skip
this step and go straight to Step 2 (treat the invocation as "sync this worktree's `.venv`/`node_modules`").
Detect it with `git rev-parse --git-dir` vs `--git-common-dir` (they differ inside a linked worktree) or
by comparing `git rev-parse --show-toplevel` to the first entry of `git worktree list`. Create no branch
and no worktree, and do not call `EnterWorktree`.

**Already inside a worktree.** Because this skill is `disable-model-invocation`, it only runs when the
user types `/new-worktree`. Typed with no task text inside an existing worktree (such as one the Claude
desktop app made), it means "Step 2 only": run `copy-venv.sh` and report. Typed with a task description
inside a worktree, still do Step 2 only for the current worktree, and tell the user no new worktree was
created (they should run it from the primary checkout for that).

1. Derive a slug from the user's task text: lowercase, non-alphanumeric → `-`, collapse/trim repeated
   dashes, cap at ~40 chars (e.g. "fix gallery thumbnails" → `fix-gallery-thumbnails`).
2. Create the worktree with a **plain `git worktree add -b <branch> <path>` and no explicit
   start-point** — git then defaults to the current `HEAD`, so the new branch always forks from
   whatever branch is currently checked out. Do **not** delegate this to `EnterWorktree`'s own creation
   path (`name` parameter): its default `baseRef: fresh` branches from `origin/<default-branch>`
   instead, and that's a mutable per-session setting this skill must not depend on.
   - **Claude Code** (the `EnterWorktree` tool is available):
     ```bash
     git worktree add -b worktree-<slug> .claude/worktrees/<slug>
     ```
     Then call `EnterWorktree({ path: ".claude/worktrees/<slug>" })` — the "enter an existing worktree"
     mode — purely to get the session's cwd switched and registered for `ExitWorktree` cleanup later.
     Do not pass `name` to `EnterWorktree` for this skill.
   - **Cursor** (no `EnterWorktree` tool):
     ```bash
     git worktree add -b cursor/<slug> "$HOME/.cursor/worktrees/<slug>"
     ```
     matching the branch/path convention `apply-worktree`/`delete-worktree` already expect. Continue
     working from that path (e.g. via a terminal `cd`, or however the IDE surfaces the new worktree).

## Step 2 — copy or regenerate `.venv` and `node_modules`

Run the helper script from the new worktree root:

```bash
bash .cursor/skills/new-worktree/scripts/copy-venv.sh
```

An existing `.venv`/`node_modules` is inspected, not blindly refused: a `.venv` is kept only if
`spacemaker` imports from this worktree's `src/` and `pytest --version` runs; a valid one is skipped, a
broken/foreign one (e.g. unrewritten paths) is replaced by a fresh copy. `node_modules` is kept if
`@biomejs/biome` is present. Add `--force` to always replace both:

```bash
bash .cursor/skills/new-worktree/scripts/copy-venv.sh --force
```

What it does:

- Auto-detects the primary checkout as the first entry of `git worktree list` (git always lists the
  main working tree first, even when the worktree lives under `<primary>/.claude/worktrees/`). No-ops if
  run from the primary itself.
- **`.venv`**: mirrors it via `robocopy` (Windows) or `rsync` (Linux/macOS) if the primary has one,
  runs `rewrite_venv_paths.py` to fix shebangs / editable `.pth` files / `direct_url.json` / Windows
  trampolines for every `uv` workspace member (`spacemaker`, `codenav-mcp`, `webnav-mcp`,
  `mcp-nav-shared` — `uv sync` alone does not fix these after a raw copy,
  https://github.com/astral-sh/uv/issues/18196), then runs an offline `uv sync --group dev` to confirm
  the lock is satisfied (retries online if that fails). Falls back straight to `uv sync --group dev` if
  the primary has no `.venv` yet.
- **`node_modules`**: mirrors it the same way (no rewrite step needed — SpaceMaker's devDependencies
  are all registry packages, so the npm-generated `.bin/*.cmd` shims carry no absolute paths). Falls
  back to `npm ci` if the primary has none. Verifies `node_modules/@biomejs/biome` exists afterward
  (the same check `scripts/quality/web.sh` uses).
- Verifies `spacemaker.__file__` resolves under the new worktree's `src/` (not the primary's), that
  `pytest --version` runs from the worktree's own venv, and that
  `node_modules/@biomejs/biome` is present.

Report to the user: the new branch name and path, and the script's verification output (or point out
what failed).

## Edge cases

| Situation | What happens |
|-----------|--------------|
| Invoked from inside a worktree, not the primary checkout | Step 1 is skipped; Step 2 runs in place to (re)sync that worktree's `.venv`/`node_modules`. |
| Destination already has a valid `.venv`/`node_modules` | `copy-venv.sh` skips them (no work); `--force` replaces them. |
| Destination has a broken/foreign `.venv` or incomplete `node_modules` | `copy-venv.sh` replaces it with a fresh copy + path rewrite. |
| Primary checkout has no `.venv` yet | `copy-venv.sh` regenerates with `uv sync --group dev` instead of copying. |
| Primary checkout has no `node_modules` yet | `copy-venv.sh` regenerates with `npm ci` instead of copying. |
| `git worktree list` yields no entry | `copy-venv.sh` aborts with a diagnostic message. |
| `rsync` missing (Linux/macOS) | `copy-venv.sh` aborts and asks to install `rsync`. |
| Shebang / `spacemaker.__file__` still points at the primary after rewrite | `copy-venv.sh` exits non-zero — do not treat the copy as successful. |

## Rules

- Always branch from the current `HEAD`, never `main`/`origin/main`, regardless of what the
  `worktree.baseRef` setting happens to be — this skill sets up its own `git worktree add`, it does not
  rely on `EnterWorktree`'s default branch selection.
- Never force-push. Never update git config. Do not use `-i` git flags.
- Does not merge/apply changes (`/apply-worktree`) or delete the worktree (`/delete-worktree`) — those
  are separate skills.
