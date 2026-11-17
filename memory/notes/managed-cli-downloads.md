---
name: managed-cli-downloads
description: pinned CLIs downloaded into user data dirs (managed, then catalog, then PATH), not bundled
type: decision
date: 2026-09-22
status: current
supersedes: bundled-clis-legal-pack
superseded_by:
source:
---

Portable release: managed CLI downloads (not bundled in exe).

- **Context:** Public release should be a single portable executable without embedding large third-party CLIs; users still need pinned, working dependency versions.
- **Decision:** Download pinned tools into OS-specific user data dirs (`managed_tools_dir()`); resolution order managed → catalog download → `PATH`; Components UI on first run; About & Legal **Delete downloaded components**. Catalog in `packaging/tool-catalog.json`; ffmpeg/ffprobe via `static-ffmpeg` PyPI wheel; adb via versioned platform-tools zip. No traditional installer. Reverses “bundle all CLIs inside artifact” v1 decision.
- **Rationale:** Smaller portable binary; updatable pins; graceful fallback when upstream download fails; aligns with user-requested portable model.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-22 — Portable release: managed CLI downloads (not bundled in exe)".

Also replaces: [bundle-adb-per-os](bundle-adb-per-os.md).
