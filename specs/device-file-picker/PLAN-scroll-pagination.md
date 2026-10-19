# Plan — scroll-driven pagination for the phone file picker

_Status: **plan only**, nothing implemented. Branch `worktree-paginated-adb-listing`. Drafted 2026-10-19._

Scope: the in-app phone picker (`web/src/device-picker.ts`) used by **USB file transfer** (`web/src/usb.ts`) and **USB photo backup** (`web/src/wizard-extras.ts`, `originLabel: "USB photo backup"`). Both go through `POST /api/device/list`, so one change covers both.

## What exists today (and why it still feels like "fetch 500 at once")

| Layer | Today | Problem |
|---|---|---|
| Domain `device_browse.py` | `BROWSE_PAGE_SIZE = 500`; `page_entries()` sorts the full list and slices `[cursor, cursor+500)` (int offset cursor) | First paint waits for 500 rows; offset cursors skip/duplicate if the folder changes between pages |
| Use case `ListDeviceDirectory.execute` | Calls `repository.list_directory()` **on every page** | "Show 500 more" re-runs the whole `adb shell find … -exec stat` (or AFC `scandir`) of the folder |
| Adapters | `adb_repository.list_directory` / `afc_repository.list_directory`, no cache | The SPEC's "≤ 30 s listing cache per (device, path)" was never implemented |
| Route `routes/device.py` | `cursor: int`, no `limit`, no filter | Client can't ask for smaller pages |
| Web `device-picker.ts` | Manual **Show 500 more** button; `renderRows()` rebuilds the whole `<ul>` each time; typing in the filter calls `loadMore(true)` = fetch **every** page | Filter on a 5 000-item DCIM folder pulls everything; full DOM rebuild per page; a page-N error replaces the whole list with an error panel |

## Target behaviour

1. Opening a folder lists it on the device **once** (one adb shell / one scandir), caches the sorted listing briefly on the server, and returns only the **first 100** entries.
2. As the user scrolls near the bottom of the list, the next 100 load automatically (IntersectionObserver sentinel — same pattern as `gallery-timeline.ts` `setupGalleryIntersectionObserver`). Rows are **appended**, never rebuilt.
3. Filter text and the "show hidden" toggle are applied **server-side** over the cached listing, so filtering never downloads the whole folder; changing them restarts at page 1 (cheap: cache hit).
4. Cursors are **keyset** (opaque string encoding the sort key of the last row), so a re-list after cache expiry neither skips nor duplicates rows.
5. A failing next-page fetch shows an inline "Couldn't load more — Retry" row at the bottom; already-loaded rows and selections stay.
6. Footer keeps "Showing N of M items" (M = filtered total). The button stays as an accessible fallback labelled **Load more** (also used when IntersectionObserver is unavailable).

## Phase gates (per AGENTS.md — one approval each)

### Phase 0 — Wireframe (`wireframes/app.html`, device-picker section ~L2950 / script ~L4934) — **done, approved 2026-10-19**
- Replace "Show 500 more" with auto-load sentinel + "Load more" fallback; add a "Loading more…" row and an inline "Couldn't load more · Retry" row; footer copy unchanged.
- **Stop for UX approval.**

### Phase 1 — Spec (`specs/device-file-picker/SPEC.md`) — **done, approved 2026-10-19**
- Design decisions row "Performance & resource budget": page = 100 entries (server bound 1..500); listing cache **implemented** (TTL 30 s, LRU ≤ 8 directories, keyed `(method, device_id, path)`; bypassed by `refresh: true`); filter/hidden server-side; one device call per directory open + one per refresh/expiry.
- API line: `POST /api/device/list` `{ method, device_id, path, cursor?: string|null, limit?: int, query?: string, show_hidden?: bool, refresh?: bool }` → `{ path, entries, next_cursor: string|null, total, total_unfiltered }`; invalid cursor → 400 `invalid_cursor`.
- Rewrite BDD around L125 ("Show 500 more") into: first page of 100; scrolling loads the next page without a new device call; filter on a 3 412-item folder returns matches without loading all pages; folder changed after cache expiry → no duplicate/skipped rows; page-2 failure keeps page 1 and shows Retry; Load more fallback works by keyboard.
- **Stop for spec approval.**

### Phase 2 — Architecture (domain + ports) — **stubs landed 2026-10-19 (new `scroll` path beside the old `execute`), pending approval**
- `domain/device_browse.py`: `BROWSE_PAGE_SIZE = 100`, `BROWSE_PAGE_MAX = 500`; `DeviceDirectoryPage.next_cursor: str | None`, add `total_unfiltered`; `encode_browse_cursor(entry)` / `decode_browse_cursor(text)` (raises `DeviceBrowseError(INVALID_PATH…)` → new kind `INVALID_CURSOR`); `page_entries(path, entries, *, after: str | None, limit, query, show_hidden)` = sort → filter → keyset slice.
- `application/device_listing_cache.py` (new, pure): `DeviceListingCache(clock: Callable[[], float], ttl=30.0, max_dirs=8)` with `get_or_list(key, loader, refresh)`; clock injected for tests. Owned by `AppServices` (the use case is built per request in `services/core.py:203`, so the cache must live on the long-lived services object and be passed in).
- `ListDeviceDirectory.__init__(repository, cache)`; `execute(device_id, path, *, cursor, limit, query, show_hidden, refresh)`.
- `DeviceRepositoryPort.list_directory` **unchanged** (adapters stay dumb).
- **Stop for approval.**

### Phase 3 — Tests (fast-tests skill, given/when/then)
- `tests/unit/test_device_browse.py`: keyset paging across 250 entries (no dupes/skips, folders first), cursor survives insert/delete of earlier names, filter + hidden, bad cursor.
- `tests/unit/test_device_listing_cache.py` (new): hit within TTL, miss after TTL (fake clock), LRU eviction, `refresh` bypass, errors not cached.
- `tests/unit/test_list_device_directory.py`: two pages → one `list_directory` call on a fake repo.
- Route tests (`test_usb_transfer_browse.py` or a new `test_device_list_route.py`): `limit` bounded, string cursor, 400 on invalid cursor.
- `web/src/device-picker.test.ts`: sentinel triggers fetch once (no double-fetch while in flight), rows appended not rebuilt (existing `<li>` identity kept), stale `requestId` responses dropped, filter debounce → single request with `query`, inline retry row.

### Phase 4 — Implementation
- Backend: domain + cache + use case + `routes/device.py` + `models.py` `DeviceListBody` + `services/usb_browse.py` (`list_device_directory` signature; `_usb_browse_snapshot` root probe shares the cache) + `services/core.py` wiring.
- Web: `device-picker.ts` (`appendRows()` split from `renderRows()`, sentinel `<li id="dp-sentinel">`, `loading` flag, 200 ms filter debounce sending `query`, hidden toggle sends `show_hidden`), `types.ts` (`DeviceListPage.next_cursor: string | null`), `index.html` (button label/fallback markup), CSS in the picker stylesheet; `npm run build:web` to regenerate `static/js/`.
- Docs: `docs/ARCHITECTURE.md` mention of the listing cache; `memory/decisions.md` entry (keyset cursor + server-side filter + cache location).

### Phase 5 — Grade
- `code-grader` subagent against `specs/device-file-picker/SPEC.md`, diff base `main`.

## Execution with Sonnet subagents

Main session (Opus) owns gates, reviews every diff, runs `uv run task checks`, and talks to you. Each step below is one `Agent` call with `model: "sonnet"`, run **after** its gate is approved. Each prompt pastes one concrete codenav/webnav call (e.g. `symbol_info(name="page_entries")`, `symbol_info(name="loadMore")`) and the tabs-indentation rule.

| # | Agent (sonnet) | Files it may touch | Depends on |
|---|---|---|---|
| A | Wireframe | `wireframes/app.html` | — |
| B | Spec rewrite | `specs/device-file-picker/SPEC.md` | A approved |
| C | Domain + ports | `domain/device_browse.py`, `application/device_listing_cache.py`, `application/list_device_directory.py` (signatures/stubs) | B approved |
| D | Backend tests + impl | `tests/unit/test_device_*`, `test_list_device_directory.py`, route test, `routes/device.py`, `models.py`, `services/usb_browse.py`, `services/core.py`, the C files' bodies | C approved |
| E | Web tests + impl | `web/src/device-picker.ts`, `device-picker.test.ts`, `types.ts`, `static/index.html`, picker CSS, `static/js/` (build output) | C approved (API contract fixed) |

D and E touch disjoint files and can run **in parallel** (two background agents). Main session then runs the full gate, the grader (Phase 5), and fixes FAILs (max 2 rounds).

## Open decisions for you

1. **Page size** — 100 (recommended; ~15 KB JSON, one screenful×3) or keep 500 with auto-load?
2. **Device-side lazy stat** (out of scope for this plan, possible follow-up): list names only (`ls -1Ap`) and `stat` just the visible page. Bigger win for 10 k+ folders, but toybox `ls` can't safely represent names containing newlines, so it needs a fallback path. Recommend deferring until the cache + scroll paging is measured on a real phone.
3. Keep the **Load more** button visible as a fallback (recommended), or hide it whenever IntersectionObserver exists?

## Out of scope
- Recursion / folder size totals; Wi-Fi method; changing the `DeviceRepositoryPort` contract; gallery pagination.
