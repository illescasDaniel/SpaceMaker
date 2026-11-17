---
name: phone-video-posters-range-route
description: first frame via a loopback token Range route; ffmpeg whitelists; own 16-thread limiter avoids self-deadlock
type: decision
date: 2026-10-20
status: current
supersedes:
superseded_by:
source:
---

Phone video posters: first frame over a loopback token-gated Range route, no playback.

- **Context:** Phase B of `specs/device-file-picker/PLAN-media-preview.md`. B0 spike on a Pixel 10a: 10 of 12 clips are HEVC and `moov` is at the tail for 11 of 12; the bundled PyQt6-WebEngine answers `canPlayType` "no" for H.264/HEVC/AAC.
- **Decision:**
  - Posters only (first frame + duration); playback moves to Phase B2.
  - ffmpeg reads the phone file through `GET /api/device/stream?token=…` (loopback-only, one Range of at most 4 MiB, `adb exec-out dd` / AFC seek+read). Tokens are 128-bit, bound to one file and size, held in an in-memory `DeviceStreamTokens` registry in `application/` (no port) and revoked in a `finally`.
  - ffmpeg is locked down with `-protocol_whitelist http,tcp` and `-format_whitelist mov,mp4,m4a,3gp,3g2,mj2,matroska,webm`, a 20 s timeout, and is killed on client abort.
  - The stream route has its own 16-thread `CapacityLimiter`; posters share the 4 per-device slots with photos, and the slot wait is bounded.
- **Rationale:** a first frame costs about 1 s and 4.5 MB even with `moov` at the tail, so no full pull. The demuxer whitelist stops a DASH/HLS manifest disguised as `.mp4` from making ffmpeg fetch other URLs (verified by hand). The separate limiter prevents a self-deadlock where preview requests hold every threadpool thread while waiting on ffmpeg's own stream sub-requests.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-20 — Phone video posters: first frame over a loopback token-gated Range route, no playback".
