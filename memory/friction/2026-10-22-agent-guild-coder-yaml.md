---
date: 2026-10-22
area: tooling
severity: wrong-result
status: open
---

**Call:** `.venv/bin/python -m pytest tests/unit/test_agent_context.py -q` after agent-guild 1.3.0 installed Cursor language coders.
**Expected:** All native agent YAML frontmatter parses.
**Got:** PyYAML ScannerError in the existing Claude language coders: an unquoted `description:` contains `(.py/.pyi): an architect` (and the TypeScript equivalent). The new Cursor twins quote correctly and expose the old Claude issue in the context-pair test.
**Workaround:** Quote the full Claude description value with a JSON-compatible YAML string; preserve matching Cursor descriptions. Keep bodies unchanged.
**Idea:** Serialize YAML frontmatter rather than interpolating raw descriptions; parse all generated agent files in installer tests.

**Local upstream fix (2026-10-22):** Implemented in `/home/daniel/Projects/Code/Agents/claude-agents` with regression coverage; 53 tests pass and the built wheel passes an install smoke test away from the checkout. Uncommitted and unreleased, so this entry stays open until published.
