# Plan — grid view in the phone picker

_Drafted 2026-10-21. Status: wireframe, spec and architecture approved 2026-10-21 (in chat); Phases 3–4 done (Sonnet subagents), gate green; Phase 5 grader PASS (round 2)._ A new SDD revision of [SPEC.md](SPEC.md): a **View** control in the picker toolbar with three modes, **Auto · List · Grid**. Execution: Sonnet subagents draft each phase; the main session reviews each one and stops at every gate.

## Naming

**Grid**, not "Gallery": *Gallery* is already the name of the library tab (`specs/gallery/`), so a second "Gallery" inside the phone picker would be ambiguous. Control label: **View**, with options **Auto**, **List** and **Grid**, as a three-segment control (`role="radiogroup"`).

## Behaviour (proposal, to be confirmed at Phase 0/1)

- **List** is today's picker, unchanged.
- **Grid** shows square tiles in auto-fill columns (about 140 px, two or three columns at 520 px or less). Each tile has the existing 320 px thumbnail or video poster (with ▶ and the duration badge), a checkbox overlay at the top left (always visible, large hit area), a 👁 preview button, and the name on one truncated line below the image. A folder tile shows 📁 and opens the folder on click. A non-media file tile shows 📄. In grid the header row (Name / Size / Modified) is hidden and the **Sort** `<select>` is shown at every width.
- **Tile click** toggles the selection, which is the fast way to pick many photos (**decided** 2026-10-21). 👁 and Enter on the focused tile open the lightbox, and Space toggles the selection. A folder tile click opens the folder.
- **Resolution order** (decided 2026-10-21): **the user's choice for this folder → the folder type → auto-detection.**
  - **User choice, per folder:** pressing **List** or **Grid** remembers that mode for the current folder only (key: device-relative path, shared by every device). Pressing **Auto** forgets it. The preferences hold at most **500** folders, LRU; the oldest entry is dropped first. Stored as `device_picker_views` in user preferences and validated on read (a bad entry is ignored). Settings → **Clear preferences** empties it. The control shows the stored mode of the folder being viewed (Auto when none is stored).
  - **Folder type:** the nearest ancestor (or the folder itself) whose name matches, case-insensitive, picks the layout.
    - **Grid:** `DCIM`, `Pictures`, `Movies`, `Screenshots`, `Camera`, `WhatsApp Images`, `WhatsApp Video`, `Telegram Images`, `Telegram Video`.
    - **List:** `Documents`, `Download`, `Android`, `Music`, `Podcasts`, `Recordings`.
    - Examples: DCIM/Camera and Pictures/Instagram → Grid; Documents/anything → List; DCIM itself → Grid of folder tiles.
    - The domain owns the table, and the server reports the resolved type on page 1 (`folder_view`), so the client holds no copy of it. The full-panel loading state keeps the layout in effect before the open; page 1 then applies the resolved one. Browsing within a photo tree (DCIM → Camera) therefore already loads in grid shape. The wireframe's instant grid skeleton uses a client copy of the table, a demo shortcut.
  - **Auto-detection** (no stored choice, no folder type) runs when page 1 arrives: **Grid** when `media_count ≥ 1` and `media_count ≥ 60 %` of the visible entries (folders + files; hidden entries count only while **Show hidden** is on), **List** otherwise.
    - The minimum used to be 3. It was lowered because a two-screenshot folder should be a grid.
    - The decision is made **once per folder open**: filter, sort and hidden-toggle restarts do not flip it.
  - The counts (`entry_count`, `media_count`) come from the **server**, computed over the cached listing with the hidden rule applied and `query` ignored. They cost no device call. The media extension set moves to the domain, the single source for both sides.
  - When Auto is active, the control shows what it resolved to and why: "Auto · Grid (photo folder)" or "Auto · List".
- **Unchanged:** pagination (sentinel, “Loading more…”, **Load more**, the inline Retry), states, ticks across folders, the lightbox (it steps the same photo + video order), thumbnail lifecycle (IntersectionObserver, ≤ 4 in flight, aborts), `kind: "folders"` disabled checkboxes, `mediaOnly` dimming, and the desktop-only boundary. Switching the mode re-renders the loaded rows in the new layout without a new request, and keeps the scroll at the first visible item where possible, the ticks, and the in-flight thumbnail cache.
- **Accessibility:** the grid is a `<ul>` of tiles (no `role="grid"` keyboard model in v1). Every tile keeps a real checkbox and the `Preview <name>` button labels. The View control is keyboard operable and its change is announced in the existing polite live region (“Grid view”).

## Phases

| Phase | Owner | Deliverable | Gate |
|---|---|---|---|
| 0 Wireframe | Sonnet subagent, reviewed here | `wireframes/app.html` `#view-device-picker`: View segmented control, grid layout of the DCIM → Camera demo, folder/document/video tiles, narrow (≤ 520 px) grid, a demo toggle showing Auto picking each layout, reviewer + agent `wf-note`s | **Stop: UX approval** |
| 1 Spec | Sonnet drafts, reviewed here | `SPEC.md` revision: metadata line, Design decisions rows (success, failure, perf: re-render of ≤ N loaded rows without a refetch, trust: `view` enum), Visual rules, Behaviour, BDD scenarios (Auto picks grid / list, no flip on filter, manual override remembered, mode switch keeps ticks/scroll, folder tile opens, grid sort menu, narrow grid, counts ignore query, Clear preferences), Out of scope | **Stop: spec approval** |
| 2 Architecture | main session | `domain/` media-extension set, `DeviceViewMode` enum, folder-type table + `resolve_folder_view(path)`, `entry_count`/`media_count`/`folder_view`/`stored_view` on `DeviceDirectoryScrollPage`; `UserPreferencesPort.get/set_device_picker_views` (bounded per-folder map, + stubs) | **Stop: approval** |
| 3 Tests | Sonnet subagent | pytest (counts, view pref round-trip and invalid value, route field validation) + vitest (auto decision, no flip on restart, mode switch keeps ticks, tile rendering) | run tests |
| 4 Implementation | Sonnet subagent(s) | use case + adapter + route, `web/src/device-picker.ts` (likely a `device-picker-grid.ts` split, since the file is 975 lines), `static/index.html`, CSS | gate green (`uv run task checks`) |
| 5 Grade | `code-grader` | scorecard against the revised SPEC | fix FAILs, max 2 rounds |

## Out of scope (v1)

- Tile size slider and pinch zoom.
- Range selection (Shift-click).
- Grid in the library Gallery (that is a different feature).
- Arrow-key 2-D navigation between tiles.
