---
name: prepend-package-manager-bins-to-path
description: Homebrew and ~/.local/bin prepended to PATH at start so host-installed tools resolve
type: decision
date: 2026-09-30
status: current
supersedes:
superseded_by:
source:
---

Prepend Homebrew / host package-manager bins to PATH.

- **Context:** Components could not resolve brew-installed `ffmpeg`/`magick`/`exiftool` after install. macOS GUI launches (and some IDE-spawned processes) get a minimal PATH without `/opt/homebrew/bin` or `/usr/local/bin`. Same class of gap as Windows ImageMagick under Program Files. Separately, PATH fallback remains gated until Components **Continue** (`components_setup_complete`); user’s marker was absent.
- **Decision:** `ensure_host_tool_path_dirs()` at `desktop.main` and `AppServices` start prepends existing well-known dirs (macOS Homebrew bin/sbin, Linux `~/.local/bin`). `resolve_tool_path` also probes those dirs when `which` misses. Continue gate unchanged.
- **Rationale:** Mutating PATH covers `shutil.which` and PATH-only deps (adbfs, idevice_*); probe covers resolve even if PATH was reset. Avoids shelling out to `brew --prefix`.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-30 — Prepend Homebrew / host package-manager bins to PATH".
