---
name: phone-picker-keyset-cursor-listing-cache
description: 30 s TTL / LRU 8 listing cache, 100-entry keyset pages, filtering server-side
type: decision
date: 2026-10-19
status: current
supersedes:
superseded_by:
source:
---

Phone picker pages by keyset cursor over an application-level listing cache.

- **Context:** every "Show 500 more" re-ran the full `adb shell find … stat`, filtering pulled every page, and the spec's 30 s listing cache was never built.
- **Decision:** `DeviceListingCache` (application layer, `ClockPort`, TTL 30 s, LRU 8, errors not cached, `refresh` bypass) lives on `AppServices` and is passed to each per-request `ListDeviceDirectory`; pages of 100 continue strictly after an opaque keyset cursor (`v1.` + base64 JSON of the sort key); filter and hidden toggle are applied server-side; `DeviceRepositoryPort` unchanged. The offset cursor path (`execute`, `page_entries`, `BROWSE_PAGE_SIZE`) was removed.
- **Rationale:** one device call per folder open, no skipped/duplicated rows when the folder changes, filtering never downloads the whole folder. Device-side lazy stat deferred (toybox `ls` cannot represent newline names). Spec: `specs/device-file-picker/SPEC.md` (revision approved).

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-19 — Phone picker pages by keyset cursor over an application-level listing cache".
