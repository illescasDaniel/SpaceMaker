---
name: ffmpeg-out-time-ms-microseconds
description: ffmpeg's out_time_ms progress value is in microseconds, which made export progress jump to 99%
type: gotcha
date: 2026-10-02
status: current
supersedes:
superseded_by:
source:
---

ffmpeg's `-progress` key `out_time_ms` is in microseconds, not milliseconds. Treating it as milliseconds made H.264 export progress jump to 99%. Fixed in the pre-1.0 pass (commit 4133173, "ffmpeg progress units").

Source: jevmem note #44.
