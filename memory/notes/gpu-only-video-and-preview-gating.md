---
name: gpu-only-video-and-preview-gating
description: video encodes on GPU only (AV1 then H.264 HW, else move as-is); gallery MP4 hidden without HW
type: decision
date: 2026-09-22
status: superseded
supersedes:
superseded_by: gallery-batch-trash-and-cpu-export
source:
---

GPU-only library video convert and gallery preview gating.

- **Context:** CPU AV1/x264 encodes are slow and HEVC library outputs do not preview in the web gallery; users on machines without HW encoders still need files in `converted/`.
- **Decision:** Detect ffmpeg HW encoders once per process: AV1 (nvenc/qsv/vaapi) preferred, else H.264 HW → `{stem}.h264.mp4`; else move video to `converted/` unchanged. Friendly MP4 export uses the same HW H.264 path; UI hides **Download as MP4** when no HW encoder. Gallery item API exposes `preview_in_browser` (excludes HEVC). Easy mode shows image-only counts in `error/` and `invalid/`.
- **Rationale:** Matches web playback constraints; avoids silent CPU transcodes; keeps Easy users informed without a full bucket browser.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-22 — GPU-only library video convert and gallery preview gating".

Superseded by [gallery-batch-trash-and-cpu-export](gallery-batch-trash-and-cpu-export.md): gallery MP4 export may now use CPU libx264 after a confirm; library convert stays GPU-only.
