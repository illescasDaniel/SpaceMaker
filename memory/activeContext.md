_Last updated: 2026-10-20 (phone picker video posters: Phase 4 done, Phase 5 grader round 2)_

## Branch

`main`. Phone-picker scroll pagination merged from `worktree-paginated-adb-listing` (`specs/device-file-picker/PLAN-scroll-pagination.md`; SDD phases 0–5 done, grader PASS). Not yet tried against a real phone.

webnav `npx --yes webnav-ts-mcp@^0.2.0`; codenav `codenav-mcp>=0.2.0,<0.3`; jevmem `>=0.4.0,<0.5`. Secret gate on `smart-commit-guard` 0.2.0.

## Current focus

Unified **Add more (files or folders)** button (v1.2.2): implemented and committed on `main`, waiting for the user to test on a real phone before publishing. See `memory/progress.md`.

Phone picker **video posters** (Phase B of `specs/device-file-picker/PLAN-media-preview.md`; `SPEC.md` "Video posters" revision, approved 2026-10-20): Phases 0–4 done, Phase 5 grader PASS (round 2; round 1 findings fixed), gate green (1195 py, 165 vitest), checked against the real Pixel. Uncommitted on `main` (new: `domain/device_stream.py`, `application/{device_stream_tokens,read_device_stream}.py`, `ports/outbound/video_poster.py`, `adapters/outbound/media/ffmpeg_video_poster.py`, loopback `GET /api/device/stream`). Next: commit; Phase B2 (playback, needs a codec answer for Qt WebEngine) and Phase C (RAW previews) are later revisions.

Phone picker **photo previews** (Phase A): committed `84a05f7` + `2ef79bd`.

Phone picker **sorting** (Name / Size / Modified, asc/desc; folders always first; remembered; sort restarts page 1 server-side, keyset cursor must carry the sort): **Phase 0 wireframe drafted** in `wireframes/app.html` `#view-device-picker` (sortable header buttons + `#dp-sort-select` below 520 px). Wireframe approved 2026-10-19. Spec revision approved 2026-10-19. **Phase 2 drafted** (gate green): `domain/device_browse.py` `DeviceBrowseSortKey` / `SortOrder` / `DeviceBrowseSort` / `DEFAULT_BROWSE_SORT`, `DeviceBrowseQuery.sort`, `DeviceDirectoryScrollPage.sort`; stubs `parse_device_browse_sort`, `entry_order_key`, `encode_sorted_cursor` / `decode_sorted_cursor`; `UserPreferencesPort.get/set_device_picker_sort` (+ `JsonUserPreferences` NotImplementedError stubs so ty stays green); `ListDeviceDirectory(..., preferences=)`. Phase 2 approved; `entry_order_key` now returns `Callable[[DeviceEntry], OrderKey]` (comparable Protocol) so `sorted` type-checks. **Phases 3–5 done** (Sonnet subagents for tests and implementation): domain `entry_order_key` (cmp_to_key total order) and `v2.` cursor, v1 helpers removed; `ListDeviceDirectory` resolves request → stored → default sort and saves explicit changes after success; `JsonUserPreferences` `device_picker_sort`; `DeviceListBody` `sort`/`order` Literals + together-or-neither validator; route echoes `sort`/`order`; web `setSort`/`renderSort` in `device-picker.ts`, markup in `static/index.html`, CSS in `shell-layout.css` (global `.sr-only` replaces `legend.sr-only`). Gate green (865 py, 124 vitest). Grader PASS; its small findings were fixed (process notes removed from docstrings, duplicate CSS removed, memory updated); no timing test was added for the 50 ms budget (~10–14 ms measured by hand). Uncommitted on `main`. Next: try it on a real phone (including the ≤520 px Sort menu), then commit. Image previews are a separate later revision (needs a real-phone spike).

Auto-retry of empty ADB/AFC device lists (3 s, max 5 retries; specs `usb-file-transfer` + `extract-media` "Automatic re-detection", approved): Phases 0-4 done. `web/src/device-retry.ts` (+ `isActive` guard) wired into `usb.ts` / `jobs.ts`, 10 vitest tests, gate green, grader round 1 fixed. Not tried with a real phone; uncommitted.

Branch `claude/device-file-picker-48a91d`: phone picker (desktop-only, grader PASS), USB transfer destination selector (`usb_transfer_destination`, persisted in preferences JSON), and LAN access policy (`web/lan_policy.py` default-deny allow-list middleware, registered inside the passcode guard so LAN gets 401 before 403; shell keyed on TCP peer, not Host; `GET /` for LAN = notice page with Open gallery). Gate green. Next: Phase 5 grader on lan-access, then report to parent session. Known edge: same-machine browser via its own LAN IP sees the notice page (use `localhost`).

Previous:

Nothing in flight. Latest: Components Copy buttons now use `execCommand("copy")` first (`web/src/dom.ts`), fixing the desktop-shell crash; no version bump. url-field (1.1.2) and gallery batch are committed.

## Just changed

- jevmem MCP entries have no env block: key and DB path live in `~/.jevmem/config.jsonc` (`uvx jevmem config init --api-key ...`), outside the repo. Notes default to `project:spacemaker`; `scope="global"` for personal preferences. Verified over MCP with public 0.4.0 on Claude Code and on Cursor (no-scope write lands in `project:spacemaker`, global write, recall of both; no env needed).

- jevmem 0.4.0 verified on Linux (2026-10-08): created `~/.jevmem/config.jsonc` from the old `~/.jevmem/.env` key and set `"db": "~/.jevmem/spacemaker.db"` (0.4.0 defaults to an empty `memory.db`); CLI, both hooks and the MCP (79 nodes, recall works) pass after a restart. `memory/README.md` Setup paragraph updated.

- smart-commit-guard 0.3.0 published (opt-in `autostart` of `ollaya serve`, doctor warns on shared hooks committed without the exec bit); hooks, CI and docs pinned `>=0.3,<0.4`; `.githooks/commit-msg` mode fixed to 755 (was 644, so Linux ignored it); autostart enabled in this machine's user config and verified with the public build.

## Next steps

- Optional cleanup: jevmem notes 7 and 8 (Cursor test notes, one project and one global) are still in `~/.jevmem/spacemaker.db`; remove with `memory_forget` (the auto-mode classifier denied it for the agent).
- `.claude/settings.json` jevmem hooks now run `uvx --from "jevmem>=0.4.0,<0.5" jevmem hook ...` with no env prefix (DB from `config.jsonc`, scope derived from the repo name); verified both hooks return recalled notes.
