---
name: linux-appimage-tag-ci
description: Linux 1.0: pruned AppDir AppImage, SHA256SUMS, CI on v* tags only
type: decision
date: 2026-09-23
status: current
supersedes:
superseded_by:
source:
---

Linux 1.0 release: AppDir AppImage and tag-only CI.

- **Context:** PyInstaller onefile AppImages were large (~256 MB) and double-compressed; srxy uses relocatable AppDir + Qt prune; `.xz` wrap saved ~2 MB for noticeable CPU/time.
- **Decision:** Primary Linux artifact = pruned AppDir + squashfs zstd‑19 AppImage; `SHA256SUMS` on the `.AppImage` (no `.xz`). GitHub Actions `.github/workflows/appimage.yml` runs only on `v*` tags (+ optional `workflow_dispatch`), uploads artifact, attaches to GitHub Release. Version **1.0.0** and maintainer contact centralized in `app_meta` / `pyproject.toml`.
- **Rationale:** WebEngine floor limits shrink margin; AppDir avoids onefile overhead; tag-only CI matches release cadence and avoids main-branch build cost.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-23 — Linux 1.0 release: AppDir AppImage and tag-only CI".
