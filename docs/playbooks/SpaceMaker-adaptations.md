# SpaceMaker adaptations

How this repo differs from generic hexagonal/SDD playbooks.

## Package layout

Use `src/spacemaker/` with `domain/`, `ports/inbound|outbound/`, `application/`, `adapters/inbound|outbound/` — not a separate `Infrastructure/` tree. See [ARCHITECTURE.md](../ARCHITECTURE.md).

## Wireframe gate

GamesLibrary has no wireframe folder. SpaceMaker requires `wireframes/*.html` **before** `specs/<feature>/SPEC.md` for UI changes. Production static UI must match approved wireframes.

## Library root folders

| Folder | Purpose |
|--------|---------|
| `originals/` | Extract target; convert consumes and empties |
| `converted/` | Gallery index; encodes and moved-as-is files |
| `error/` | Encode failed after one automatic retry |
| `invalid/` | Unsupported type or unreadable/broken media |

## Conversion policy (summary)

Authoritative compression flags: [convert_all_1_1.sh](../reference/convert_all_1_1.sh). Behavior:

**Move as-is (no re-encode)** from `originals/` → `converted/`:

- Images already AVIF
- Videos already AV1 and web-compatible
- Web-compatible videos at ≤ 1.5 Mbps bitrate

**Web-compatible (video):** container mp4/webm/mov; video h264/hevc/vp9/av1; audio (if present) aac/mp3/opus/vorbis/flac.

**Web-compatible (image, size rollback only):** jpg/jpeg/png/webp/gif/avif — not RAW/HEIC/TIFF/JXL.

**Encode images** to AVIF: ImageMagick `-depth 10 -quality 80 -define avif:chroma-subsampling=444`; ExifTool copy all tags from source. RAW fallback: PreviewImage then JpgFromRaw; if none → `invalid/`.

**DNG + JPEG same stem:** RAW → `stem.avif`; JPEG → `stem_jpg.avif` or `stem_jpeg.avif`; both outputs required.

**Encode videos** to `stem.av1.mp4`: encoder priority nvenc → qsv → vaapi → libsvtav1 (flags per reference script); Opus 256k; faststart.

**Size rollback:** if output > original + 10% and source is web-compatible, discard output and move original to `converted/`. Otherwise keep encode and remove source from `originals/`.

**Failures:** unsupported/broken → `invalid/`. Encode fail → delete partial, retry once; still fail → `error/`. Successful encode → output in `converted/`, source removed from `originals/`.

**UI:** warning when `error/` or `invalid/` non-empty — Review; for errors, also Move to converted (unchanged files).

## Desktop shell

Local FastAPI + static UI in pywebview; no cloud dependency. Gallery may expose LAN URL + QR (spec/wireframe).

## Device extract (MTP default, ADB recommended)

- UI default: **MTP**. Alternate: **ADB (recommended)** with info (ⓘ) for setup steps.
- Hexagonal: `DeviceRepository` port; adapters `MtpDeviceRepository`, `AdbDeviceRepository` (adbutils on all OSes for ADB).
- **MTP:** One **libmtp** adapter on all OSes; **bundle** libmtp CLI in release artifacts.
- **ADB:** **adbutils** + **bundled** `adb` per OS/CPU.
- **Convert:** **bundled** ffmpeg, ffprobe, magick, exiftool — see `packaging/third-party-manifest.yaml`.
- **Legal:** ship privacy, disclaimer, third-party notice in installer + in-app About (`specs/legal/SPEC.md`).
- **Move** from device: prefer ADB; MTP move may be unsupported per file.
- Spec: [specs/extract-media/SPEC.md](../../specs/extract-media/SPEC.md).

## Testing

No real ffmpeg/adb in unit tests. Integration tests mock subprocess or use fixtures. See [fast-tests.md](fast-tests.md).
