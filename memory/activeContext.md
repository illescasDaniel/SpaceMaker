_Last updated: 2026-09-26_

## Branch

`cursor/fix-raw-dng-convert-test-2e72`

## Current focus

Fixed failing DNG embedded-preview convert unit test. Root cause was the
fake `magick` stub in `tests/unit/test_raw_image_convert.py`: bash
`${@: -1}` under `#!/bin/sh` (dash) → exit 2 "Bad substitution", so both
the DNG encode and the post-preview encode failed and the file landed in
`error/`. Stub now uses POSIX last-arg (`for dest; do :; done`) and exits
1 when the encode source is `*.dng` so the real preview fallback path runs.

## Next steps

- None for this thread; PR/merge of the test stub fix when ready.

## Run

```bash
uv run pytest tests/unit/test_raw_image_convert.py -vv
uv run task checks
```
