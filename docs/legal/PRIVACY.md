# SpaceMaker Privacy Policy

_Last updated: 2026-09-22_

## Summary

SpaceMaker runs on your computer. It is designed to **backup, convert, and browse your media locally**. We do not operate a cloud service that stores your photos or videos.

## Data we process

| Data | Where it stays | Sent to us? |
|------|----------------|-------------|
| Photos and videos from your phone | Your chosen library folder on disk | **No** |
| Device identifiers (USB/MTP/ADB) | Local app memory only | **No** |
| Conversion logs | Local machine (optional log files) | **No** |

## Network use

- **LAN gallery (optional):** If you open Step 3 “Visualize”, SpaceMaker may bind a web server on your local network so your phone can view the gallery. Traffic stays on your LAN; no account is required.
- **LAN upload (optional):** If you use Step 1 **Wi‑Fi** extract, SpaceMaker shows a QR code so your phone can **send** files to your PC library while an extract session is active. Uploads require the session token from that QR/URL; traffic stays on your LAN.
- **Updates (future):** If auto-update is added later, the spec will require explicit opt-in and an updated policy.

## Third-party programs

SpaceMaker **bundles** command-line tools (FFmpeg, ImageMagick, ExifTool, libmtp, Android platform-tools `adb`, etc.) so you do not download them separately. See [THIRD_PARTY_TOOLS.md](THIRD_PARTY_TOOLS.md) for names, purposes, project home pages, and license notes.

Those tools run **only on your machine** as part of SpaceMaker. We do not receive their output.

## Telemetry

v1 release builds: **no analytics telemetry** unless explicitly documented in a future spec and this policy.

## Contact

Project maintainer contact: _contact@daniel-ir.eu_.
