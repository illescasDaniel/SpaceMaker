---
date: 2026-09-29
area: codenav
severity: missing-feature
status: open
---

**Call:** `implementations(port_name="FileSystemPort")`
**Expected:** `LocalFileSystem` plus the test double `tests/unit/fakes.py:FakeFileSystem` (same for `FakeDeviceRepository`, `FakeMediaConverter`, …).
**Got:** only `LocalFileSystem` — `CODENAV_MCP_SOURCE_ROOT=src` scopes the candidate scan, so fakes never show. When changing a port, the fakes are exactly what an agent must also update.
**Workaround:** grep `tests/` for `class Fake`.
**Idea:** an `include_tests`/extra-roots option (or a second env var for "also scan these roots, labelled"), reporting fakes under a separate heading.
