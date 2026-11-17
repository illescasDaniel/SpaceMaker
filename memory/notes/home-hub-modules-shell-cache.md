---
name: home-hub-modules-shell-cache
description: Home hub modules, one LAN session at a time; versioned WebEngine profile dir
type: decision
date: 2026-09-23
status: current
supersedes:
superseded_by:
source:
---

Home hub modules and Qt WebEngine shell cache.

- **Context:** Single default UI needed distinct flows (photo backup, USB wizard, receive/send files); pywebview kept serving stale HTML/JS while the browser showed updates.
- **Decision:** `AppModule` + one LAN session at a time; Home hub tiles; phone `/receive` and `/share` pages; `UI_SHELL_VERSION` drives a versioned WebEngine profile dir and `?_shell=` entry URL; no-cache headers on shell assets. Receive **Open documents folder** opens `{Documents}/SpaceMaker` when present, else Documents; Linux `xdg-open` targets directories directly (not parent only).
- **Rationale:** Clear module boundaries; avoids silent cache mismatch in desktop shell; file-manager open matches user path expectations on Linux.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-23 — Home hub modules and Qt WebEngine shell cache".
