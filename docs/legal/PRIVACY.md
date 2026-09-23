# SpaceMaker Privacy Policy

_Last updated: 2026-09-23_

## Summary

SpaceMaker runs on your computer. It is designed to **backup, convert, and browse your media locally**. We do not operate a cloud service that stores your photos or videos.

## Data we process

| Data | Where it stays | Sent to us? |
|------|----------------|-------------|
| Photos and videos from your phone | Your chosen library folder on disk (or Documents for Receive files) | **No** |
| Device identifiers (USB/MTP/ADB) | Local app memory only | **No** |
| Conversion logs | Local machine (optional log files) | **No** |

## Network use

- **Third-party tool downloads (first launch):** SpaceMaker may download pinned command-line tools (FFmpeg, Android platform-tools, etc.) from official upstream sites or package indexes into a folder on your computer. Your media is not uploaded as part of this step.
- **LAN gallery (optional):** From the **Gallery** tab (or after convert), SpaceMaker may bind a web server on your local network so your phone can browse converted media via QR. Traffic stays on your LAN; no account is required.
- **LAN upload to library (optional):** **Photo backup** (Wi‑Fi) shows a QR code so your phone can send files into your library `originals/` while a session is active. Uploads require the session token from that QR/URL; traffic stays on your LAN.
- **Receive files (optional):** From Home → **Receive files**, a QR opens a page where your phone can upload into `Documents/SpaceMaker/` (or your platform’s Documents equivalent). Token required; LAN only.
- **Send files (optional):** From Home → **Send files**, you pick files or folders on the PC; your phone downloads them via a tokenized `/share` page. LAN only.
- **Desktop control vs phone access:** Settings, extract/convert, share selection, and similar **control** APIs are accepted only from the app on this computer (loopback). Phone features use separate tokenized URLs or the open gallery QR as described above.
- **Updates (future):** If auto-update is added later, the spec will require explicit opt-in and an updated policy.

## Third-party programs

SpaceMaker uses command-line tools (FFmpeg, ImageMagick, ExifTool, libmtp, Android platform-tools `adb`, etc.). Release builds **download** pinned versions when possible; otherwise they may use tools you installed on your system. See [THIRD_PARTY_TOOLS.md](THIRD_PARTY_TOOLS.md) for names, purposes, project home pages, and license notes.

Those tools run **only on your machine** as part of SpaceMaker. We do not receive their output.

## Telemetry

v1 release builds: **no analytics telemetry** unless explicitly documented in a future spec and this policy.

## Contact

**Daniel Illescas Romero** — [contact@daniel-ir.eu](mailto:contact@daniel-ir.eu)
