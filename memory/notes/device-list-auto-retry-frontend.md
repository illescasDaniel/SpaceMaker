---
name: device-list-auto-retry-frontend
description: empty ADB/iPhone list retries every 3 s, max 5, in the UI only; backend stays stateless
type: decision
date: 2026-10-19
status: current
supersedes:
superseded_by:
source:
---

Empty ADB/iPhone device list auto-retries in the frontend only.

- **Context:** the first `GET /api/devices` sometimes returns empty (adb daemon starting / authorization settling); the status stayed "No device found" until the user switched method.
- **Decision:** a shared `web/src/device-retry.ts` helper retries every 3 s, max 5 times, used by USB file transfer and photo-extract Step 1; no domain type, port or API change. Specs: `usb-file-transfer` and `extract-media` "Automatic re-detection".
- **Rationale:** the policy is UI timing, not business logic; the backend call is unchanged and stays stateless (no background polling loop server-side).

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-19 — Empty ADB/iPhone device list auto-retries in the frontend only".
