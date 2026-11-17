---
name: mkdocs-build-warning-free
description: the mkdocs docs build must stay warning-free
type: preference
date: 2026-09-30
status: current
supersedes:
superseded_by:
source:
---

The MkDocs build of `docs/` must stay warning-free. Decided on 2026-09-30 when the MCP packages moved out to their PyPI releases.

**How to apply:** after changing docs or `mkdocs.yml`, run a strict build (`mkdocs build --strict` into a temp dir) and fix warnings.

Source: jevmem note #35.
