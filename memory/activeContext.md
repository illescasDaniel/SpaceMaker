_Last updated: 2026-09-22_

## Branch

`main`

## Current focus

**Phase 4 wizard + convert path stable** — bundled tools policy, extract/convert UX, device detection. **Gallery / Step 3 Visualize** has known issues; another agent owns that next.

## Just changed (session)

- Bundled-only `tools/` resolution, `dev-tools` task, README; graceful `/api/devices` 503 + UI errors
- Convert: nested `converted/` mkdir, failure messages, skip `.thumbnails` on extract + library scan
- Device: GVFS usability, reconcile stale `device_id`, status only when device in current scan
- Library root normalization; Qt WebEngine shutdown helper

## Next steps (other agent)

1. Fix **Visualize** column and **gallery** view (timeline/QR/routing)
2. Phase 4 packaging: PyInstaller + pinned binaries in `tools/`

## Run

```bash
uv run task dev-tools -- --from-path
uv run task spacemaker
uv run task checks
```
