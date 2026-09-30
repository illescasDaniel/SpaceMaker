# Third-party tools used by SpaceMaker

SpaceMaker runs these **external programs** on your computer for extract and convert. Official portable builds **download pinned versions** into your user data folder on first launch. If a download fails, install the tool yourself (package manager or vendor site) and ensure it is on your `PATH`.

Machine-readable manifest: [packaging/third-party-manifest.yaml](https://github.com/illescasDaniel/SpaceMaker/blob/main/packaging/third-party-manifest.yaml). Download pins: [packaging/tool-catalog.json](https://github.com/illescasDaniel/SpaceMaker/blob/main/packaging/tool-catalog.json).

| Tool | Purpose in SpaceMaker | Project home |
|------|------------------------|--------------|
| **adb** | Copy/move files from Android (ADB mode) | https://developer.android.com/tools/releases/platform-tools |
| **adbfs** | USB file transfer Add files/folder + exist-probe mount (PATH only; e.g. `adbfs-rootless-git`) | https://github.com/spion/adbfs-rootless |
| **idevice_id**, **idevicepair**, **ideviceinfo**, **ifuse** (libimobiledevice) | iPhone USB / DCIM (Linux, system `PATH` only) | https://libimobiledevice.org/ |
| **ffmpeg** | Encode video to AV1 / H.264 | https://ffmpeg.org/ |
| **ffprobe** | Validate videos; read bitrate/duration | https://ffmpeg.org/ |
| **magick** (ImageMagick) | Auto-orient; thumbs; friendly JPEG; AVIF identify / non-progressive AVIF fallback | https://imagemagick.org/ |
| **avifenc** (libavif) | Progressive (layered) library image → AVIF | https://github.com/AOMediaCodec/libavif |
| **exiftool** | Copy EXIF/metadata to AVIF outputs | https://exiftool.org/ |

## Licenses

License texts shipped inside upstream archives are stored next to the downloaded binaries when available. Summaries:

- **adb / platform-tools:** Android SDK Platform Tools License (Google)
- **adbfs-rootless:** BSD-3-Clause (system package; not catalog-downloaded)
- **libimobiledevice / ifuse:** LGPL-2.1+
- **FFmpeg / ffprobe:** LGPL or GPL depending on build configuration (documented per release)
- **ImageMagick:** ImageMagick License
- **libavif / avifenc:** BSD-2-Clause
- **ExifTool:** Artistic License / GPL (variant documented per release)

SpaceMaker’s own license is in the repository [LICENSE](../../LICENSE) file (MIT).

## Bundled web assets (UI)

| Asset | Purpose | License |
|-------|---------|---------|
| **Font Awesome Free** 6.x (solid chevrons in gallery) | Self-hosted under `static/vendor/fontawesome/` | [Font Awesome Free License](https://fontawesome.com/license/free) (icons: CC BY 4.0; fonts: SIL OFL 1.1; code: MIT) — full text in `static/vendor/fontawesome/LICENSE.txt` |

## Updates to downloaded tools

Version pins live in [packaging/tool-catalog.json](https://github.com/illescasDaniel/SpaceMaker/blob/main/packaging/tool-catalog.json). Security updates may ship in patch releases without changing this document’s structure.

## Removing downloads

In **Settings**, use **Delete downloaded components** to remove only the managed tools folder. System packages are not uninstalled.
