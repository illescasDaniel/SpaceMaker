_Last updated: 2026-09-22_

## Branch

`main` — push skipped per user.

## Current focus

Manual smoke for Easy issue counts and video preview/MP4 gating; Phase 4 packaging when ready.

## Just changed (this commit)

- Easy: **image_import_issues** line (images in `error/` + `invalid/`)
- Video convert: HW AV1 → else HW H.264 → else move-as-is; no CPU encoders; `.h264.mp4` fallback output
- Gallery: `preview_in_browser` for HEVC etc.; hide **Download as MP4** when no HW encoder
- Specs/playbooks updated (convert-media, easy-mode, gallery)

## Next steps

1. Manual smoke: Easy issue counts after failed image convert; HEVC item without preview; MP4 button on/off by HW
2. Phase 4 packaging (open)

## Run

```bash
uv run task spacemaker
uv run task checks
```
