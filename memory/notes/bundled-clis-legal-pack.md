---
name: bundled-clis-legal-pack
description: all manifest CLIs bundled per OS/arch, with a legal pack
type: decision
date: 2026-09-22
status: superseded
supersedes:
superseded_by: managed-cli-downloads
source:
---

Bundled CLIs + legal pack.

- **Context:** User requires no manual third-party installs; privacy policy, third-party home pages, disclaimer in installer.
- **Decision:** All manifest tools bundled per OS/arch; `resolve_tool_path()` frozen vs dev. Docs in `docs/legal/`; spec `specs/legal/SPEC.md`; manifest YAML synced to `BundledTool` enum via tests.
- **Rationale:** Self-contained desktop product; transparency and liability coverage before public release.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-22 — Bundled CLIs + legal pack".

Superseded by [managed-cli-downloads](managed-cli-downloads.md).
