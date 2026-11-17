---
name: phone-picker-grid-view-resolution
description: per-folder choice, then folder-type table, then auto-detect (>=1 media, >=60%); counts server-side
type: decision
date: 2026-10-21
status: current
supersedes:
superseded_by:
source:
---

Phone picker grid view: per-folder choice, server-side folder types and counts.

- **Context:** grid view revision of `specs/device-file-picker/SPEC.md` (plan `PLAN-grid-view.md`); the user asked for Auto / List / Grid with folder-type defaults.
- **Decision:**
  - Resolution order: the user's per-folder choice → folder-type table (nearest ancestor-or-self) → auto-detection (≥ 1 media and ≥ 60 % of visible entries).
  - The folder-type table and media extensions live in the domain (`device_view.py`, `device_media.py`); page 1 of `/api/device/list` reports `entry_count`, `media_count`, `folder_view`, `stored_view`; the client holds no copy of the table.
  - Choices are stored per folder in `device_picker_views` (≤ 500, LRU by JSON key order, so `JsonUserPreferences` no longer writes with `sort_keys`), set via loopback-only `PUT /api/device/view`; the client also keeps a session map so a failed write still holds for the app run.
  - The clear-preferences use case is now built lazily from `services.user_preferences` (`clear_user_preferences_use_case()`).
- **Rationale:** per-folder memory matches file-manager expectations without one switch disabling Auto everywhere; server-side counts are correct when page 1 is all folders and cost no device call; a single read-modify-write under the store lock avoids lost updates.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-21 — Phone picker grid view: per-folder choice, server-side folder types and counts".
