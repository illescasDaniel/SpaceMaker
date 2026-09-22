# Third-party tools bundled with SpaceMaker

SpaceMaker includes the following **external programs** inside official installers/binaries. You should not need to download or install them manually.

Machine-readable manifest: [packaging/third-party-manifest.yaml](../../packaging/third-party-manifest.yaml).

| Tool | Purpose in SpaceMaker | Project home |
|------|------------------------|--------------|
| **adb** | Copy/move files from Android (ADB mode) | https://developer.android.com/tools/releases/platform-tools |
| **mtp-detect**, **mtp-getfile** (libmtp) | MTP device access (default connection mode) | https://libmtp.sourceforge.net/ |
| **ffmpeg** | Encode video to AV1 | https://ffmpeg.org/ |
| **ffprobe** | Validate videos; read bitrate/duration | https://ffmpeg.org/ |
| **magick** (ImageMagick) | Encode images to AVIF | https://imagemagick.org/ |
| **exiftool** | Copy EXIF/metadata to AVIF outputs | https://exiftool.org/ |

## Licenses

Exact license texts for each bundled build are shipped under `packaging/licenses/` in the source repository and copied into release artifacts. Summaries:

- **adb / platform-tools:** Android SDK Platform Tools License (Google)
- **libmtp:** LGPL-2.1+
- **FFmpeg / ffprobe:** LGPL or GPL depending on build configuration (documented per release)
- **ImageMagick:** ImageMagick License
- **ExifTool:** Artistic License / GPL (variant documented per release)

SpaceMaker’s own license is stated in the repository `LICENSE` file (to be added before public release).

## Updates to bundled tools

Version pins live under `packaging/*.version` files. Security updates may ship in patch releases without changing this document’s structure.
