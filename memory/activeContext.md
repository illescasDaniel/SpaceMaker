_Last updated: 2026-09-23_

## Branch

`main`

## Current focus

Shipped **iPhone USB (AFC)**, **extract/convert stop + shutdown**, and **desktop CSP** fixes on `main`.

## Just changed (committed)

- Linux **iPhone (USB)** wizard method + `AfcDeviceRepository` (scoped DCIM walk, PATH libimobiledevice/ifuse)
- Extract stop waits for USB thread; **Stop convert**; clean desktop shutdown
- Loopback CSP allows `unsafe-eval` for pywebview; directive separator test prevents malformed headers

## Next steps

1. Manual: iPhone USB extract → Stop extract → convert only when count stable
2. Manual: Stop convert; quit app → port 8765 free
3. Easy-mode import panels — await spec approval (separate track)

## Run

```bash
uv run task spacemaker
uv run task checks
```
