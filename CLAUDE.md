@AGENTS.md

## Agents and delegation

You are the orchestrator: delegate to the `architect`, `coder`, `code-grader` and `utility` subagents in
`.claude/agents/`, and own every approval gate and memory write. Routing, briefs and the memory protocol:

@.claude/development-workflow.md

## Python code goes to `coder-python`

Any task that adds, changes, renames, moves or deletes `.py`/`.pyi` code goes to `coder-python`, not the generic
`coder`: it uses the project's `codenav` MCP for type-checked navigation and refactoring. Keep `coder` for everything
else, and split a task that spans languages.

## TypeScript code goes to `coder-typescript`

Any task that adds, changes, renames, moves or deletes JavaScript/TypeScript/HTML/CSS (`.ts`, `.tsx`, `.js`, `.jsx`,
`.html`, `.css`) code goes to `coder-typescript`, not the generic `coder`: it uses the project's `webnav` MCP for
type-checked navigation and refactoring. Keep `coder` for everything else, and split a task that spans languages.
