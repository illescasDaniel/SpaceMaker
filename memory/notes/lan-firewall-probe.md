---
name: lan-firewall-probe
description: firewalld/UFW probe and LAN self-test exposed in server-info
type: decision
date: 2026-09-22
status: current
supersedes:
superseded_by:
source:
---

LAN firewall probe in bootstrap.

- **Context:** Phone gallery failed when UFW blocked TCP 8765; users need in-app hints without guessing.
- **Decision:** `bootstrap/firewall.py` probes firewalld/UFW rules and a LAN TCP self-test; expose via `/api/server-info.firewall`. Shell helper `scripts/firewall/allow-spacemaker-port.sh` + task `firewall-allow`. Do not run MTP reconcile on every settings snapshot (blocks gallery clients).
- **Rationale:** Detection is best-effort but actionable; device scans stay on `/api/devices` only.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-22 — LAN firewall probe in bootstrap".
