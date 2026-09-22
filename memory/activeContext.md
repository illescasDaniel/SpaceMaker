_Last updated: 2026-09-22_

## Branch

`main`

## Current focus

**Gallery item page + SDD gate policy** — committed locally; no git remote configured.

## Just changed (session)

- Gallery: item page, metadata, Download / JPEG / MP4 export (`.exports` cache, WS progress)
- Governance: explicit design + spec chat approval before `src/` (AGENTS.md, sdd.mdc, sdd-feature skill, playbooks)

## Next steps

1. Phase 4 packaging: PyInstaller + pinned binaries in `tools/`
2. Optional: LAN phone smoke test of gallery item + export

## Run

```bash
uv run task dev-tools -- --from-path
uv run task spacemaker
uv run task checks
```
