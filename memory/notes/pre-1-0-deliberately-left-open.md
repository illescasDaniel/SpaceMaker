---
name: pre-1-0-deliberately-left-open
description: left open after the pre-1.0 review: tool-catalog sha256 pinning, ADB list-all-roots speed, LAN delete/export auth
type: context
date: 2026-10-02
status: current
supersedes:
superseded_by:
source:
---

The pre-1.0 review (2026-10-02, commit 4133173) deliberately left three items open: sha256 pinning of tool-catalog downloads (needs real downloads to compute the hashes), speeding up ADB list-all-roots, and authentication for LAN delete/export beyond the passcode.

State on 2026-11-17: `packaging/tool-catalog.json` still has no sha256 field. ADB listing was later rebuilt (in-app picker with a listing cache, 2026-10-19). LAN access became default-deny (2026-10-19), but gallery delete/export stay reachable from LAN behind the optional passcode.

Source: jevmem note #48; `memory/progress.md` pre-1.0 item.
