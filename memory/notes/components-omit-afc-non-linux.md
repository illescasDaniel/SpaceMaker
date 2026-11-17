---
name: components-omit-afc-non-linux
description: Components hides AFC tools (idevice_*, ifuse) on macOS and Windows
type: decision
date: 2026-09-30
status: current
supersedes:
superseded_by:
source:
---

Components omits AFC tools on macOS/Windows.

- **Context:** Components recommended `brew install ifuse` on macOS even though iPhone USB/AFC is Linux-only; Homebrew often has no ifuse bottle on current macOS.
- **Decision:** `components_tools(platform=…)` filters `idevice_*` / `ifuse` out of Components status, ensure, downloads_pending, and chip counts on non-Linux. Drop those keys from `_MACOS_FORMULAS` / `_MACOS_PACKAGES`. `BundledTool` enum unchanged for Linux adapters.
- **Rationale:** Matches extract-media Linux-only AFC scope; stops false MISSING / dead brew hints on Mac/Windows.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-30 — Components omits AFC tools on macOS/Windows".
