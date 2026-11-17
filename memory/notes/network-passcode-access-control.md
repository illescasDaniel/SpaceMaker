---
name: network-passcode-access-control
description: scrypt passcode + HMAC cookie, not AES: plain-http LAN pages have no WebCrypto; record in its own 0600 file
type: decision
date: 2026-10-02
status: current
supersedes:
superseded_by:
source:
---

Network passcode is access control, not AES encryption.

- **Context:** user wanted a passcode to stop LAN devices deleting gallery items / calling endpoints, initially imagined as AES encryption of all data.
- **Decision:** salted-scrypt passcode + HMAC login cookie, one inbound middleware, QR URLs carry a random token in the `#k=` fragment; record stored in its own `network_passcode.json` (0600) so Clear preferences / Reset library never disable it. No data or transport encryption.
- **Rationale:** phones load `http://<lan-ip>`, which is not a secure context (no WebCrypto); ffmpeg/avifenc/thumbnails need plaintext files. Access control fixes the stated problem; TLS/at-rest encryption stay future work.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-02 — Network passcode is access control, not AES encryption".
