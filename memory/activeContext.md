_Last updated: 2026-09-23_

## Branch

`main` — Home hub + receive/send committed locally; push skipped per user.

## Current focus

**Easy mode import issues (SDD)** — wireframe approved; spec draft in `specs/easy-mode/SPEC.md`; await spec approval for panels + open-folder UX on Photo backup.

## Just changed (saved commit)

- Home hub (four tiles), module LAN sessions, receive/share phone pages, breadcrumbs, QR ⓘ
- Qt WebEngine shell versioning; port-in-use guard; receive **Open documents folder** gating + Linux folder reveal fix
- Specs: `home-modules`, `receive-files`, `send-files`; wireframes + phone mocks

## Next steps

1. User: **spec approved** for easy-mode import issues → implement panels
2. Manual LAN test: all four modules on phone
3. `git push` when ready

## Run

```bash
uv run task spacemaker
uv run task checks
uv run task build-installer   # → dist/SpaceMaker (gitignored)
uv run task build-appimage    # → dist/SpaceMaker-<ver>-<arch>.AppImage (~225M zstd) + .xz
uv run task build-installer   # Linux → dist/spacemaker-linux.AppDir
```
