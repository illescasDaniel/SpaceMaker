---
name: lan-loopback-control-plane
description: desktop control APIs loopback-only; gallery and tokenized pages open on LAN
type: decision
date: 2026-09-23
status: superseded
supersedes:
superseded_by: lan-access-default-deny-allowlist
source:
---

LAN server: loopback-only desktop control plane.

- **Context:** FastAPI binds `0.0.0.0` for phone QR/LAN gallery, but mutating APIs, `GET /api/settings`, and `/ws` exposed full session state (including upload/receive/share token URLs) to any LAN client.
- **Decision:** `require_loopback()` on `request.client.host` for desktop control APIs and WebSocket; phone gallery (list/media/thumbs/delete/export) and tokenized upload/receive/share stay reachable on LAN; drop `library_root` query override on gallery endpoints; resolve converted paths with `Path.relative_to`.
- **Rationale:** Matches trusted-PC / untrusted-LAN model without adding gallery QR tokens (product choice deferred).

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-23 — LAN server: loopback-only desktop control plane".

Superseded by [lan-access-default-deny-allowlist](lan-access-default-deny-allowlist.md).
