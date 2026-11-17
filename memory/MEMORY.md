# Memory

Code at HEAD wins for current behaviour; notes win for why and history; newest current note wins; open `source` sessions for detail.
Migrated on 2026-11-17 from the legacy memory bank (`decisions.md`, `progress.md`, `friction/`) and the jevmem/agemem notes; the old project files were moved to trash; the active friction log remains.

## Topics
- [Agent workflow and memory](topics/agent-workflow.md) 21 notes: How agents work in this repo: SDD gates, subagents, rules and skills, and where memory lives.
- [Dev tooling and quality gate](topics/dev-tooling.md) 13 notes: Quality gate, secret scanning, dependency audit, worktrees and docs build.
- [codenav and webnav MCP servers](topics/mcp-navigation.md) 29 notes: The code-navigation MCP servers agents use here, how they were built and where they live now.
- [Phone access over USB](topics/device-usb.md) 17 notes: How SpaceMaker reaches Android and iPhone over USB, and the in-app phone picker.
- [Library and media conversion](topics/conversion.md) 14 notes: Library folders, what gets encoded or moved, encoders, and file-safety rules.
- [Gallery](topics/gallery.md) 15 notes: The processed/ gallery: index, thumbnails, item page, batch actions and export.
- [LAN access and file transfer](topics/lan-transfer.md) 8 notes: What phones on the network can reach, the passcode, and the send/receive/transfer flows.
- [Desktop shell](topics/desktop-shell.md) 19 notes: The desktop window: pywebview backends, Qt WebEngine quirks, shell versioning and shared UI components.
- [Packaging and releases](topics/packaging.md) 15 notes: Release artifacts per OS, managed CLI downloads, and the Components screen.

## Newest notes
- [SDD moves to one HTML page per feature](notes/sdd-html-feature-pages.md) 2026-11-17: new features use one sdd/<feature>.html page per feature; legacy specs/, wireframes/, design/ kept untouched
- [Memory moved to memory-1; memory bank, jevmem and agemem retired](notes/memory-1-replaces-memory-bank-jevmem.md) 2026-11-17: memory-1 replaced the memory bank, jevmem and agemem; old project files moved to trash; shared jevmem database retained
- [Agentic-loadout 0.8.0 replaces agent-guild](notes/agentic-loadout-0-8.md) 2026-11-17: agentic-loadout 0.8.0 (formerly agent-guild): orchestrator + small/large coder tiers, Entire session history
- [Phone RAW (DNG) previews: embedded JPEG located by a pure-Python IFD parser over range reads](notes/phone-raw-dng-preview-ifd-parser.md) 2026-10-21: stdlib IFD parser over range reads finds the DNG's embedded JPEG; ~0.2 s instead of 8-27 MB pulls
- [Phone picker grid view: per-folder choice, server-side folder types and counts](notes/phone-picker-grid-view-resolution.md) 2026-10-21: per-folder choice, then folder-type table, then auto-detect (>=1 media, >=60%); counts server-side
- [adb exec-out merges stderr into stdout](notes/adb-exec-out-merges-stderr.md) 2026-10-21: adb exec-out merges remote stderr into stdout: dd needs status=none or ranges get ~80 extra bytes
- [Phone video posters: first frame over a loopback token-gated Range route, no playback](notes/phone-video-posters-range-route.md) 2026-10-20: first frame via a loopback token Range route; ffmpeg whitelists; own 16-thread limiter avoids self-deadlock
- [Phone photo thumbnails: 64 KB head read for the EXIF thumbnail, full pull as the fallback](notes/phone-photo-thumbs-64kb-head-read.md) 2026-10-20: EXIF thumbnail from the first 64 KB (97% of camera JPEGs); full pull <=25 MB as fallback; 4 parallel reads
- [Phone picker sorting is server-side with a sort-aware v2 cursor and a server-stored preference](notes/phone-picker-server-side-sort-v2-cursor.md) 2026-10-19: sort carried in a v2 keyset cursor; preference stored server-side; cross-sort cursors rejected
- [In-app phone picker over `adb shell` replaces adbfs + native dialog](notes/phone-picker-replaces-adbfs.md) 2026-10-19: one in-app picker over adb shell / ifuse for USB transfer and photo backup; adbfs and native dialog removed
- [Phone picker pages by keyset cursor over an application-level listing cache](notes/phone-picker-keyset-cursor-listing-cache.md) 2026-10-19: 30 s TTL / LRU 8 listing cache, 100-entry keyset pages, filtering server-side
- [LAN access: default-deny allow-list keyed on the TCP peer](notes/lan-access-default-deny-allowlist.md) 2026-10-19: non-loopback peers reach only an allow-list (403 desktop-only otherwise); shell chosen by TCP peer, not Host
- [Empty ADB/iPhone device list auto-retries in the frontend only](notes/device-list-auto-retry-frontend.md) 2026-10-19: empty ADB/iPhone list retries every 3 s, max 5, in the UI only; backend stays stateless
- [Clipboard API fails in the pywebview Qt shell](notes/pywebview-qt-clipboard-permission.md) 2026-10-18: navigator.clipboard fails in the pywebview Qt shell (feature-permission TypeError); use execCommand first
- [One ⓘ helper and one URL field component for the desktop UI](notes/info-panels-and-url-field-components.md) 2026-10-18: one info-panel binding and one copyable URL field; execCommand fallback because LAN pages are plain http
- [Gallery batch: send2trash, CPU libx264 behind a confirm, zips in `.exports/.batch`](notes/gallery-batch-trash-and-cpu-export.md) 2026-10-18: send2trash only (no hard delete); gallery MP4 export may use CPU libx264 after a 409 confirm; library convert stays GPU-only
- [Secret gate on smart-commit-guard 0.3](notes/smart-commit-guard-0-3.md) 2026-10-08: secret gate on smart-commit-guard >=0.3,<0.4 (autostarts the local model); commit-msg hook must be 755
- [webnav pinned to `webnav-ts-mcp@^0.2.0` (write tools + write queue)](notes/webnav-ts-mcp-0-2-write-queue.md) 2026-10-05: webnav-ts-mcp ^0.2.0 serializes write tools; a local ~/.claude.json override had shadowed .mcp.json
- [Dependency audit in the quality gate, plus Dependabot](notes/dependency-audit-and-dependabot.md) 2026-10-05: pip-audit on the exported lock + npm audit (high) end the quality gate; weekly grouped Dependabot
- [Items left open after the pre-1.0 review](notes/pre-1-0-deliberately-left-open.md) 2026-10-02: left open after the pre-1.0 review: tool-catalog sha256 pinning, ADB list-all-roots speed, LAN delete/export auth

## History (superseded)
Superseded notes are listed on their topic page.
