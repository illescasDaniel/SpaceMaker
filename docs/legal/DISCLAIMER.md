# Disclaimer

SpaceMaker helps you **copy, convert, and organize** media from mobile devices. **You are responsible for your data.**

## Backup and data loss

- **Copy vs Move:** If you choose **Move** during extract, files may be **removed from your phone** after a successful transfer. If you choose **Convert**, files may be **removed from `originals/`** after successful conversion or move-as-is rules.
- **Failures:** Failed conversions may place files in `error/` or `invalid/`. Interrupted jobs may leave partial files; SpaceMaker attempts idempotent retries but **cannot guarantee** recovery in every situation.
- **Keep backups** of anything you cannot afford to lose. Test with **Copy** mode first if you are unsure.

## No warranty

SpaceMaker is provided **“as is”** without warranty of any kind, express or implied, including fitness for a particular purpose and non-infringement.

## Limitation of liability

To the maximum extent permitted by law, the authors and contributors **are not liable** for any direct, indirect, incidental, or consequential damages — including **loss of photos, videos, or other files** — arising from use or inability to use SpaceMaker, bundled third-party tools, or device connection failures.

## Third-party tools

Bundled utilities (FFmpeg, ImageMagick, ExifTool, libmtp, adb, etc.) are independent projects. SpaceMaker invokes them locally; their behavior and licenses are described in [THIRD_PARTY_TOOLS.md](THIRD_PARTY_TOOLS.md).

## Your acceptance

Installing or running SpaceMaker indicates that you have read this disclaimer and the [Privacy Policy](PRIVACY.md).
