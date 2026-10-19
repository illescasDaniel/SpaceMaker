_Last updated: 2026-10-19 (Components Copy button fix, committed)_

## Branch

`main`. webnav `npx --yes webnav-ts-mcp@^0.2.0`; codenav `codenav-mcp>=0.2.0,<0.3`; jevmem `>=0.4.0,<0.5`. Secret gate on `smart-commit-guard` 0.2.0.

## Current focus

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
