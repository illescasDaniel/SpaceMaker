---
name: appimage-ci-ubuntu-24-libasound
description: AppImage CI on Ubuntu 24.04 needs libasound2t64, and dist/ must exist before packing on a clean checkout
type: gotcha
date: 2026-10-02
status: current
supersedes:
superseded_by:
source:
---

On the Ubuntu 24.04 runner the AppImage job needs `libasound2t64` instead of `libasound2`, and `dist/` must be created before packing on a clean checkout. Found on 2026-10-02 when `appimage.yml` became `release.yml` (Linux AppImage, Windows exe, macOS arm64/x86_64 DMGs, combined SHA256SUMS).

Source: jevmem notes #46 and #47.
