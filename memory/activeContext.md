_Last updated: 2026-09-22_

## Branch

`main`

## Current focus

**Gallery / Visualize shipped** — full SDD increment on `main`. LAN gallery UX: firewall probe, larger QR, responsive layout.

## Just changed (session)

- Gallery: Step 3 `visualize` state, `/gallery` routing, thumbs, calendar, EXIF, segno QR
- LAN: `lan_ip` fallback, skip device reconcile on settings, gallery-only init path
- Firewall: `probe_gallery_port`, Step 3 ⓘ panel, `scripts/firewall/allow-spacemaker-port.sh`, `uv run task firewall-allow`
- Agent skills: `save-changes`, `apply-worktree`, `delete-worktree` under `.cursor/skills/`

## Next steps

1. User: `sudo uv run task firewall-allow` if phone gallery still blocked (UFW enabled on CachyOS)
2. Phase 4 packaging: PyInstaller + pinned binaries in `tools/`

## Run

```bash
uv run task dev-tools -- --from-path
uv run task spacemaker
uv run task checks
```
