# Third-party tools used by SpaceMaker

SpaceMaker runs these **external programs** on your computer for extract and convert. Official portable builds **download pinned versions** into your user data folder on first launch. If a download fails, install the tool yourself (package manager or vendor site) and ensure it is on your `PATH`.

Machine-readable manifest: [packaging/third-party-manifest.yaml](../../packaging/third-party-manifest.yaml). Download pins: [packaging/tool-catalog.json](../../packaging/tool-catalog.json).

| Tool | Purpose in SpaceMaker | Project home |
|------|------------------------|--------------|
| **adb** | Copy/move files from Android (ADB mode) | https://developer.android.com/tools/releases/platform-tools |
| **mtp-detect**, **mtp-getfile** (libmtp) | MTP device access (default connection mode) | https://libmtp.sourceforge.net/ |
| **ffmpeg** | Encode video to AV1 / H.264 | https://ffmpeg.org/ |
| **ffprobe** | Validate videos; read bitrate/duration | https://ffmpeg.org/ |
| **magick** (ImageMagick) | Encode images to AVIF | https://imagemagick.org/ |
| **exiftool** | Copy EXIF/metadata to AVIF outputs | https://exiftool.org/ |

## Licenses

License texts shipped inside upstream archives are stored next to the downloaded binaries when available. Summaries:

- **adb / platform-tools:** Android SDK Platform Tools License (Google)
- **libmtp:** LGPL-2.1+
- **FFmpeg / ffprobe:** LGPL or GPL depending on build configuration (documented per release)
- **ImageMagick:** ImageMagick License
- **ExifTool:** Artistic License / GPL (variant documented per release)

SpaceMaker’s own license is in the repository [LICENSE](../../LICENSE) file (MIT).

## Updates to downloaded tools

Version pins live in [packaging/tool-catalog.json](../../packaging/tool-catalog.json). Security updates may ship in patch releases without changing this document’s structure.

## Removing downloads

In **Settings**, use **Delete downloaded components** to remove only the managed tools folder. System packages are not uninstalled.
