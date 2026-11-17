---
name: components-install-command-per-os
description: per-tool install_command by OS/distro, display-only, built in bootstrap (no new port)
type: decision
date: 2026-09-30
status: current
supersedes:
superseded_by:
source:
---

Components: per-tool install_command (OS/distro), drop screen setup_hint.

- **Context:** macOS Components failed on broken `static_ffmpeg_wheel`; users need system install one-liners under each failed/missing tool, OS-gated (brew / winget / apt|dnf|pacman|paru|yay), including adb after download failure and PATH-only CLIs. Spec approved.
- **Decision:** (1) Domain `ManagedToolStatus.install_command: str | None` — display-only; set only when `resolution` is missing (or phase failed) and a formula exists. (2) No new ports — formula map + Linux `/etc/os-release` (+ PATH probes for paru/yay/apt-get/dnf/pacman) live in `bootstrap/platform_setup_hints.py`; `ManagedToolsService.status_dict` attaches `install_command` per tool row and stops emitting screen-level `setup_hint`. (3) Catalog: remove macOS `static_ffmpeg_wheel`; delete unused wheel installer if nothing else uses it. (4) Web UI renders `.tool-install-hint` under each row; hide `#components-iphone-packages` unless Linux. (5) App never invokes package managers.
- **Rationale:** Same trust model as today’s winget hint, but per-tool and multi-OS; domain carries the field so API/snapshot stay typed without a package-manager port.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-30 — Components: per-tool install_command (OS/distro), drop screen setup_hint".
