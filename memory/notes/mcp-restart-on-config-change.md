---
name: mcp-restart-on-config-change
description: MCP servers restart on config change and warn while running stale code; richer hover; position checks
type: decision
date: 2026-09-29
status: current
supersedes:
superseded_by:
source:
---

MCP: restart on config change, warn on stale code, richer hover, position validation.

- **Context:** The re-evaluation left four open items: config that alters resolution (`pyproject.toml`, `tsconfig.json`) needed a manual restart; servers attached to a session keep old code after fixes; codenav `hover` on a variable said only `AppServices`; a wrong line/column returned "No hover information" like a real miss. A fifth (regex-grade `selector`) was reviewed and left alone: no template-literal or multi-variable selector exists in `web/src`.
- **Decision:** (1) `LspClient.config_names` files are stamped by the existing refresh walk; a change runs `restart()` + `on_restart` and posts a one-shot notice. (2) `NoticeBoard` appends `[server] …` lines to every tool result; a sticky line while the server's own source differs from startup. No self-reload. (3) codenav hover appends `typeDefinition` location/header/docstring when ty returns a bare type. (4) Positions are validated in `LspClient` (`InvalidPositionError`, in `TOOL_ERRORS`).
- **Rationale:** A fresh server is more reliable than trusting each server to re-read config (tsserver and ty differ). A stdio server can't re-handshake, so importlib reload or `exec` would leave the client inconsistent; a proxy/worker split is too much machinery for a dev tool, and a visible note fixes the actual harm (silent old answers). Not fixed: `selector` stays regex-grade until a real miss appears in `memory/friction/`.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-29 — MCP: restart on config change, warn on stale code, richer hover, position validation".
