---
date: 2026-09-29
area: codenav
severity: confusing
status: open
---

**Where:** `codenav_mcp/server.py` `_PROBE_RELATIVE_PATH = Path("mcp-servers") / ".codenav_probe.py"`; `docs/agent-tooling.md` (Protocol conformance, step 2) and `decisions.md` say `<root>/.codenav_probe.py`.
**Problem:** doc/code drift, and a SpaceMaker-specific directory name inside a server that is meant to be generic (`docs/agent-tooling.md` "Portability"). The document is in-memory only, so the directory needn't exist, but its location can affect how ty resolves the probe's imports.
**Workaround:** none needed today.
**Idea:** find out why `mcp-servers/` was chosen (git log -S), then either make it a documented env var / default to the workspace root, or fix the docs.
