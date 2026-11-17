---
name: lan-access-default-deny-allowlist
description: non-loopback peers reach only an allow-list (403 desktop-only otherwise); shell chosen by TCP peer, not Host
type: decision
date: 2026-10-19
status: current
supersedes: lan-loopback-control-plane
superseded_by:
source:
---

LAN access: default-deny allow-list keyed on the TCP peer.

- **Context:** the GUI and control APIs were reachable from any LAN device (and Host-header spoofing picked the desktop shell).
- **Decision:** non-loopback peers may reach only the allow-list in `web/lan_policy.py` (gallery, QR upload/receive/share/transfer pages and their APIs, unlock); everything else is 403 `desktop-only`; `GET /` shows a notice page. Middleware sits inside the passcode guard so unauthenticated LAN clients get 401 before 403. Shell choice uses `request.client.host`, not Host.
- **Rationale:** new routes are private by default; a route-audit test enforces it. Known edge: a same-machine browser using its own LAN IP looks remote (use `localhost`). Spec: `specs/lan-access/SPEC.md`.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-19 — LAN access: default-deny allow-list keyed on the TCP peer".
