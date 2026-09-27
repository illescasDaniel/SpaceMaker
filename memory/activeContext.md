_Last updated: 2026-09-27_

## Current focus

**USB file transfer** on `cursor/usb-file-transfer-c861` — ready to land. User verified
ADB + iPhone (AFC) USB transfer on device. MTP stripped; Browse = Add files/folder +
path flatten.

## Just changed

- Full USB transfer stack (domain/ports/use cases/ADB adbfs + AFC ifuse/UI/API/tests)
- Spec/docs/packaging: MTP removed; ADB + AFC only for cable
- Memory: flag ADB Browse performance for pre-production review

## Next steps

- Land PR (`/save-pr-changes` in flight)
- After merge: pre-prod review of slow ADB Browse / listing (see `progress.md`)
