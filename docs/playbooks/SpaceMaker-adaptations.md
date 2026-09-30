# SpaceMaker adaptations

How this repo differs from generic hexagonal/SDD playbooks.

## Package layout

Use `src/spacemaker/` with `domain/`, `ports/inbound|outbound/`, `application/`, `adapters/inbound|outbound/` — not a separate `Infrastructure/` tree. See [ARCHITECTURE.md](../ARCHITECTURE.md).

## Wireframe gate

GamesLibrary has no wireframe folder. SpaceMaker requires `wireframes/*.html` **before** `specs/<feature>/SPEC.md` for UI changes. Agents must **stop for explicit human design approval** after wireframe updates and **explicit spec approval** before any changes under `src/spacemaker/` or production static UI. Production static UI must match approved wireframes.

## Library root folders

| Folder | Purpose |
|--------|---------|
| `originals/` | Extract target; convert consumes and empties |
| `processed/` | Gallery index; encodes and moved-as-is files (legacy on-disk name `converted/` is migrated to `processed/` on library ensure) |
| `error/` | Encode failed after one automatic retry |
| `invalid/` | Unsupported type or unreadable/broken media |

## Conversion policy (summary)

Authoritative compression flags (historical shell reference): [convert_all_1_1.sh](../reference/convert_all_1_1.sh). **App runtime** uses GPU-only video encode or move-as-is (see [convert-media](https://github.com/illescasDaniel/SpaceMaker/blob/main/specs/convert-media/SPEC.md)). Behavior:

**Move as-is (no re-encode)** from `originals/` → `processed/`:

- Images already AVIF
- Videos already AV1 and web-compatible
- Web-compatible videos at ≤ 1.5 Mbps bitrate

**Web-compatible (video):** container mp4/webm/mov; video h264/hevc/vp9/av1; audio (if present) aac/mp3/opus/vorbis/flac.

**Web-compatible (image, size rollback only):** jpg/jpeg/png/webp/gif/avif — not RAW/HEIC/TIFF/JXL.

**Encode images** to progressive (layered) AVIF when `avifenc` is available: `avifenc --progressive -d 10 -q 80 -y 444` on JPEG/PNG directly; RAW via ExifTool embedded preview then `avifenc`; other formats (HEIC/TIFF/JXL/WebP/…) Magick-rasterize to temp PNG then `avifenc`. ExifTool copy all tags from source (Orientation stripped when already applied). If `avifenc` is missing, fall back to ImageMagick single-layer AVIF (`-depth 10 -quality 80 -define avif:chroma-subsampling=444`). Already-AVIF → move-as-is (not rewritten as progressive). Magick stays required for thumbs, friendly JPEG, identify, and rasterizing formats `avifenc` cannot read.

**DNG + JPEG same stem:** RAW → `stem.avif`; JPEG → `stem_jpg.avif` or `stem_jpeg.avif`; both outputs required.

**Encode videos** to `stem.av1.mp4` when AV1 hardware is available; else `stem.h264.mp4` when H.264 hardware is available. Priority: av1_nvenc → av1_qsv → av1_vaapi → h264_nvenc → h264_qsv → h264_vaapi. **No CPU video encoders.** With no hardware encoder, move source video to `processed/` unchanged. Never library-encode to HEVC. Opus 256k for AV1 outputs; AAC for H.264 outputs; faststart.

**Size rollback:** if output > original + 10% and source is web-compatible, discard output and move original to `processed/`. Otherwise keep encode and remove source from `originals/`.

**Failures:** unsupported/broken → `invalid/`. Encode fail → delete partial, retry once; still fail → `error/`. Successful encode → output in `processed/`, source removed from `originals/`.

**UI:** warning when `error/` or `invalid/` non-empty — Review; for errors, also Move to processed (unchanged files).

## Gallery export (download-friendly formats)

Separate from library convert. On-demand when the user chooses **Download as JPEG** or **Download as MP4** on a gallery item page. Outputs are cached under `{library_root}/.exports/` (skipped by extract/convert scans, like `.thumbnails/`), using an injective path-mirror of the source relative path (append `.jpg` / `.mp4` to the full relative path so distinct sources never share a cache file).

**Image → JPEG:** ImageMagick `-quality 95`; ExifTool copy all tags from source. No size rollback — quality first.

**Video → MP4:** **Hardware H.264 + AAC** only (same encoder priority as library convert). If no HW H.264 encoder is available, hide **Download as MP4** on the item page. No CPU `libx264`. No size rollback.

**Skip encode:** if the stored file is already JPEG (image action) or already H.264 + AAC in MP4 (video action), serve the stored file as the download.

Progress: WebSocket `gallery_export` events while encoding; UI alert on the item page.

## Desktop shell

Local FastAPI + static UI in pywebview; no cloud dependency. **Home hub** is the launch screen; optional LAN gallery URL + QR and tokenized upload/receive/share pages (specs).

**pywebview backend per OS:** native WebView2 (`edgechromium`) on Windows, native WKWebView (`cocoa`) on macOS — no Qt on either. **Qt WebEngine** (`qt`) stays Linux-only, so the AppImage keeps pinning a known Chromium version instead of depending on the host distro's `webkit2gtk`. `--gui` overrides the default for dev/testing; PyQt6/qtpy are Linux-only dependencies (`pyproject.toml` `sys_platform == 'linux'` markers).

## Device extract (Wi‑Fi default, ADB / iPhone USB)

- **Photo backup** (Home tile): centered Easy layout, auto Wi‑Fi receive, convert-as-received (`ui_mode=easy` internally). **Theme:** all web shells follow OS light/dark (`static/theme.css`).
- **USB photo backup** tile opens the three-step wizard (`ui_mode=advanced` internally). Wi‑Fi default; cable modes **ADB (cable)** and **iPhone (USB)** (Linux AFC) with info (ⓘ) for setup steps.
- **USB file transfer** tile: cable-only **ADB / iPhone USB (AFC)** copy or move of **any** files into `documents_directory()/SpaceMaker/` (same root as Receive files). **Add files…** / **Add folder…** use **adbfs** (ADB) or **ifuse** (AFC). Destination strips Android user-storage prefixes (`sdcard`, `storage/emulated/0`, `storage/self/primary`). No convert, no gallery, no `originals/`. Spec: [specs/usb-file-transfer/SPEC.md](https://github.com/illescasDaniel/SpaceMaker/blob/main/specs/usb-file-transfer/SPEC.md).
- Hexagonal: `DeviceRepository` port; adapters `AdbDeviceRepository`, `AfcDeviceRepository` (adbutils on all OSes for ADB).
- **iPhone USB:** **AfcDeviceRepository** on Linux — `idevice_*` + `ifuse` on `PATH`; **usbmuxd** (Arch: udev starts it on plug-in, not `systemctl enable`).
- **ADB:** **adbutils** + managed or `PATH` `adb` per OS/CPU; USB transfer Add mounts via **adbfs** on PATH (e.g. `adbfs-rootless-git`).
- **Convert:** managed or `PATH` ffmpeg, ffprobe, magick, avifenc, exiftool — see `packaging/tool-catalog.json`.
- **Legal:** ship privacy, disclaimer, third-party notice in portable binary + in-app About (`specs/legal/SPEC.md`).
- **Move** from device: prefer ADB; AFC move may be unsupported per file.
- Spec: [specs/extract-media/SPEC.md](https://github.com/illescasDaniel/SpaceMaker/blob/main/specs/extract-media/SPEC.md).
- **Not in product:** MTP / libmtp / GVFS.

## Testing

No real ffmpeg/adb in unit tests. Integration tests mock subprocess or use fixtures. See [fast-tests.md](fast-tests.md).
