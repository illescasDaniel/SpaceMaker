---
name: windows-portable-reliability
description: Windows portable fixes: opaque QR, component downloads, shutdown
type: decision
date: 2026-09-24
status: current
supersedes:
superseded_by:
source:
---

Windows portable build reliability batch (QR, component downloads, shutdown).

- **Context:** Windows dogfooding surfaced four separate rough edges in the portable build: QR codes rendered with a theme-matched (often dark) background so they were unreadable in dark mode and briefly flashed/collapsed on `src` reload; the packaged ffmpeg download URL and the ImageMagick/ExifTool story were incomplete for Windows (no ExifTool catalog entry, no fallback when winget installs ImageMagick without updating `PATH`); `start_convert`'s `STOP_EXTRACT_FIRST` policy called `stop_extract_and_wait()` unconditionally, which dropped the Easy-mode Wi‑Fi upload session on the very first "convert as received" trigger even when no extract job was actually running; and Qt WebEngine/Chromium left native threads/timers that could hang or crash on quit, worse on Windows than Linux.
- **Decision:** `adapters/inbound/web/qr_svg.py` wraps `segno` with explicit opaque `dark="#000000"/light="#ffffff"` and callers set `background: #fff` around the `<img>`; `app.js` gets a `setQrImageSrc()` helper that only reassigns `img.src` when the QR URL actually changed (was unconditional reassignment every poll, causing the flash). `packaging/tool-catalog.json` adds an `exiftool` entry via new `CatalogToolInstaller` `zip_flatten` strategy (flattens a zip's `prefix/` into the tools dir and copies a `launcher` file to the canonical bundled name); `bundled_tools.py` adds `_windows_magick_from_common_install_dirs()` (Program Files glob, PATH fallback) and `bootstrap/platform_setup_hints.py` returns a winget one-liner for the Components screen when ffmpeg/magick/exiftool are missing on Windows. `AppServices.start_convert` now only calls `stop_extract_and_wait()` under `STOP_EXTRACT_FIRST` when `self._extract_job_active()` is true.
- **Rationale:** Each fix is independently small but all were discovered together while validating the Windows portable build end-to-end; grouping them avoided four near-identical "Windows build fix" commits touching overlapping files (`app.js`, `index.html`).

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-24 — Windows portable build reliability batch (QR, component downloads, shutdown)".
