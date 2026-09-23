_Last updated: 2026-09-23_

## Branch

`main` — local commit; push skipped per user.

## Current focus

1. **Easy mode import issues (SDD):** wireframe approved; `specs/easy-mode/SPEC.md` drafted — **await spec approval**, then implement panels + `POST /api/library/open-folder`.
2. **Managed tools:** catalog download, Components screen APIs, Continue → PATH fallback; validate magick/exiftool retries and GPU ffmpeg on real convert.

## Just changed (saved commit)

- Managed CLI catalog/installer, Components APIs, persisted Continue marker, tool runner PATH preference
- RAW preview path in convert pipeline; packaging catalog/spec assets; favicon route
- Phone upload `/upload/ended` route; wireframe Easy import-issue panels
- Easy-mode spec: warn panels + open-folder actions

## Next steps

1. User: **spec approved** for easy-mode import issues → ports, tests, production UI
2. Settings/Components: retry **magick** + **exiftool**; **Continue**; re-test MOV convert with PATH GPU ffmpeg
3. `uv run task checks`

## Run

```bash
uv run task spacemaker
uv run task checks
```
