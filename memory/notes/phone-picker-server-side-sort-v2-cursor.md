---
name: phone-picker-server-side-sort-v2-cursor
description: sort carried in a v2 keyset cursor; preference stored server-side; cross-sort cursors rejected
type: decision
date: 2026-10-19
status: current
supersedes:
superseded_by:
source:
---

Phone picker sorting is server-side with a sort-aware v2 cursor and a server-stored preference.

- **Context:** the picker needs Name / Size / Modified sorting, asc/desc, while keeping keyset paging over the cached listing and remembering the choice.
- **Decision:** domain `DeviceBrowseSort(key: DeviceBrowseSortKey, order: SortOrder)` (default Name A→Z; folders always first; ties by name A→Z) on `DeviceBrowseQuery.sort` (`None` = stored preference) and echoed on `DeviceDirectoryScrollPage.sort`; new `v2.` cursor (`encode_sorted_cursor` / `decode_sorted_cursor`) carries the sort and the anchor entry, so a cursor from another sort or a `v1.` cursor is `invalid_cursor`; the preference lives in `UserPreferencesPort` (`device_picker_sort`), written by `ListDeviceDirectory` only when an explicit sort differs from the stored one after a successful listing. `v1.` helpers stay until Phase 4 swaps them out.
- **Rationale:** sorting on the client would need every page; one preference write path avoids a separate prefs endpoint; carrying the sort in the cursor makes cross-sort cursor misuse detectable. Spec: `specs/device-file-picker/SPEC.md` (sorting revision approved).

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-19 — Phone picker sorting is server-side with a sort-aware v2 cursor and a server-stored preference".
