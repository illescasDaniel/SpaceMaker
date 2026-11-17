# Agent workflow and memory
Updated: 2026-11-17. How agents work in this repo: SDD gates, subagents, rules and skills, and where memory lives.

## Now
Features go through `sdd/<feature>.html` pages with separate chat approvals ([sdd-html-feature-pages](../notes/sdd-html-feature-pages.md), [sdd-explicit-approval](../notes/sdd-explicit-approval.md)), an independent grader ([sdd-phase5-code-grader](../notes/sdd-phase5-code-grader.md)) and spec design decisions ([spec-design-decisions-section](../notes/spec-design-decisions-section.md)). Agents come from agentic-loadout 0.8.0 ([agentic-loadout-0-8](../notes/agentic-loadout-0-8.md)); memory is memory-1 ([memory-1-replaces-memory-bank-jevmem](../notes/memory-1-replaces-memory-bank-jevmem.md)).

## How it got here
- 2026-09-22 Markdown specs + wireframes before code; explicit approval required ([note](../notes/sdd-markdown-specs-test-style.md)).
- 2026-09-24 Graphify + MkDocs adopted for navigation, then removed on 2026-09-25 in favour of the codenav MCP ([note](../notes/graphify-removed-codenav-renamed.md)).
- 2026-10-03 three-way split: memory bank for state, jevmem for facts, AGENTS.md for rules ([note](../notes/memory-three-way-split.md)); jevmem pinned 0.3 → 0.3.1 → 0.4 config file.
- 2026-10-22 agent-guild 1.3.0 shared rules across Claude, Cursor and Codex ([note](../notes/agent-guild-1-3-shared-rules.md)).
- 2026-11-17 agentic-loadout 0.8.0, memory-1 and sdd-html-feature replace the above ([note](../notes/memory-1-replaces-memory-bank-jevmem.md)).

## Notes
- [Memory moved to memory-1; memory bank, jevmem and agemem retired](../notes/memory-1-replaces-memory-bank-jevmem.md) 2026-11-17: memory-1 replaced the memory bank, jevmem and agemem; old files kept as history until the user approves removal
- [Agentic-loadout 0.8.0 replaces agent-guild](../notes/agentic-loadout-0-8.md) 2026-11-17: agentic-loadout 0.8.0 (formerly agent-guild): orchestrator + small/large coder tiers, Entire session history
- [SDD moves to one HTML page per feature](../notes/sdd-html-feature-pages.md) 2026-11-17: new features use one sdd/<feature>.html page per feature; legacy specs/, wireframes/, design/ kept untouched
- [SDD Phase 5: independent `code-grader` subagent + mechanical pre-check script](../notes/sdd-phase5-code-grader.md) 2026-09-29: independent read-only code-grader after the build, max 2 fix rounds, plus mechanical pre-checks
- [SPEC.md carries four agreed "Design decisions" (success criteria, failure handling, perf/resource budget, trust boundary)](../notes/spec-design-decisions-section.md) 2026-09-29: every spec answers success criteria, failure handling, perf budget and trust boundary up front
- [Graphify removed entirely; `ty` MCP server renamed to `codenav`; AGENTS.md now instructs agents to prefer it over grep](../notes/graphify-removed-codenav-renamed.md) 2026-09-25: Graphify removed entirely; ty MCP renamed codenav; agents told to prefer it over grep
- [Lean agent context: `AGENTS.md` sole always-on source, path-scoped rules, memory archive](../notes/lean-agent-context.md) 2026-09-24: AGENTS.md the only always-on file; detail moved to path-scoped rules, docs and an archive
- [`.claude/rules/` mirrors `.cursor/rules/`: hand-maintained copies, not symlinks](../notes/claude-rules-hand-maintained-copies.md) 2026-09-24: .claude/rules are hand-maintained copies of .cursor/rules, not symlinks; drift-tested
- [`.claude/skills` symlink: relative target, and `New-Item` directory-symlink pitfall](../notes/claude-skills-symlink-relative.md) 2026-09-24: .claude/skills -> ../.cursor/skills relative; on Windows use mklink /D, not New-Item
- [SDD: explicit design + spec approval before src](../notes/sdd-explicit-approval.md) 2026-09-22: design and spec need explicit chat approval; plans and todos are not approval
- [Feature spec split](../notes/feature-spec-split.md) 2026-09-22: first four feature specs split with an index at specs/README.md

## History (superseded)
- [Agent-guild 1.3.0: shared project rules and skills across three tools](../notes/agent-guild-1-3-shared-rules.md) 2026-10-22 → superseded by agentic-loadout-0-8
- [jevmem 0.4.0: settings in `~/.jevmem/config.jsonc`, per-project default scope](../notes/jevmem-0-4-config-file.md) 2026-10-06 → superseded by memory-1-replaces-memory-bank-jevmem
- [jevmem DB path via `${USERPROFILE}` / `${userHome}`, pin 0.3.1](../notes/jevmem-db-path-userprofile.md) 2026-10-06 → superseded by jevmem-0-4-config-file
- [jevmem pinned to `jevmem>=0.3.0,<0.4`](../notes/jevmem-pin-0-3.md) 2026-10-05 → superseded by jevmem-db-path-userprofile
- [Three-way split between memory bank, jevmem and AGENTS.md](../notes/memory-three-way-split.md) 2026-10-03 → superseded by memory-1-replaces-memory-bank-jevmem
- [Graphify feedback loop (`save-result`/`reflect`) adopted; `diagnose multigraph` documented as trigger-based, not routine](../notes/graphify-feedback-loop.md) 2026-09-24 → superseded by graphify-removed-codenav-renamed
- [`graphify-out/graph.json` / `GRAPH_REPORT.md` will always show an unstaged diff right after a commit — expected, not a bug](../notes/graphify-out-diff-expected.md) 2026-09-24 → superseded by graphify-removed-codenav-renamed
- [GraphRAG agent tooling: MkDocs + Graphify (not custom AST script), CLAUDE.md merged into AGENTS.md](../notes/graphrag-mkdocs-graphify.md) 2026-09-24 → superseded by graphify-removed-codenav-renamed
- [Claude Code project-skill discovery via `.claude/skills` symlink](../notes/claude-skills-symlink.md) 2026-09-24 → superseded by claude-skills-symlink-relative
- [SDD, wireframes, and test style](../notes/sdd-markdown-specs-test-style.md) 2026-09-22 → superseded by sdd-html-feature-pages
