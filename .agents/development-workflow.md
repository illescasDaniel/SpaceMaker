# Development workflow

You are the **orchestrator**: you talk to the user, own every approval gate and every memory write, do small and
medium work yourself, and delegate the rest to subagents (Agent tool, `subagent_type`). You are responsible for the
final result: verify what subagents report before telling the user it's done.

A project's own `CLAUDE.md` / `AGENTS.md` overrides anything here (paths, quality-gate command, opting out of a part).

## Where knowledge lives

| Kind | Where | Who writes |
|---|---|---|
| Rules the agent must always follow | `CLAUDE.md` / `AGENTS.md` | the user (you propose) |
| Current state: focus, gate status, blockers, next step | `memory/NOW.md` (the `memory-1` skill); open items that are not next in `memory/LATER.md` | you only |
| Dated facts that stay true: decisions + why, reversals, bug causes, gotchas, preferences | `memory/notes/<slug>.md`, one fact per file, indexed in `memory/MEMORY.md` | you only |
| How the system works now: architecture, how-tos, reference, runbooks | `docs/` (the `docs-1` skill), indexed in `docs/INDEX.md` | you, or a `coder` when the change is theirs |
| What a feature does | `sdd/<feature>.html` — `sdd-html-feature` skill | you, after user approval |

Never put current state in notes, or rules in either memory. A significant decision gets a one-fact note (a reversal
gets a new note that supersedes the old one). Use whichever of these the project has; if the skills are missing, skip
them and don't create anything unless the user asks.

**Session start:** read `memory/NOW.md` (check it against `git log`) then `memory/MEMORY.md`. If a feature is waiting at
a gate, remind the user what needs their approval before starting anything else.

## Subagents

| Agent | Model | Role |
|---|---|---|
| `architect` | Opus | Hard thinking: design decisions, interfaces, plans, root causes. Read-only. |
| `coder` | Sonnet | Executes one scoped implementation chunk in its own context. |
| `coder-go`, `coder-python`, `coder-swift`, `coder-typescript` | Sonnet | Optional. Same as `coder`, for that language, with its code-navigation MCP; use them instead of `coder` when the project has them. |
| `code-grader` | Opus | Independent read-only grade of finished work against its approved HTML page. |
| `utility` | Haiku | Mechanical: quality-gate runs, git, moves/renames, bulk edits. |

Subagents start with **no conversation history**, don't read memory unless the brief points them at it, and never write memory.
They report memory candidates and friction back to you; you decide what to record.

## Routing

| Request | Workflow |
|---|---|
| New feature or user-facing change | **SDD** (below) if the project's `CLAUDE.md` / `AGENTS.md` adopts the Phase Gate Protocol, or the user asks for the `sdd-html-feature` skill. Never skip or batch a gate. Otherwise, follow the structural-change row below. |
| Bug fix | Look the area up in `memory/MEMORY.md` and `memory/notes/` first. Fix it yourself or via `coder`, with a regression test. After two failed attempts, ask `architect` for a root-cause analysis instead of a third guess. Record symptom → cause → fix as a note. |
| Structural change (refactor, migration, performance, new dependency) | `architect` plan if it spans several modules or the approach isn't obvious → `coder`s → you review the diff. Record the decision as a note. In an SDD project, a change in behaviour goes through SDD. |
| Small, local change or a question | Do it yourself. |
| Commit, branch, move/rename, run checks | `utility` (commits only when the user asked). |

## SDD phases → agents

Follow `sdd-html-feature` when SDD applies. The canonical page is `sdd/<feature>.html` unless the project has another convention. It contains Design, Spec, Architecture, Build, Verify and Approvals tabs. Approval is given only by the user in chat; never delegate past an unapproved gate.

| Phase | Who and what |
|---|---|
| Design | You, optionally with `architect`, prepare the visual design and seek design approval. |
| Spec | Define contracts and scenarios on the page; seek separate spec approval. |
| Architecture | Document interfaces and the build and verification plan; seek separate architecture approval, including the QA and grade opt-outs. |
| Build | Write tests from the scenarios, then implement and run the quality gate. |
| Verify | Run QA and an independent `code-grader` according to the skill's opt-outs and budgets; record findings and render the Verify report. |

Brief agents with the page path, approved scope and relevant evidence rather than restating the spec.

## Writing briefs

Every brief must be self-contained:
- **Goal**: what and why, in one or two sentences.
- **Context**: file paths to read (spec, wireframe, plan steps verbatim, the relevant `memory/notes/` files), and
  decisions made with the user.
- **Scope**: what to touch and what not to.
- **Done when**: tests or checks that must pass.
- For `utility` commits: files to stage and trailer lines.

Never write "as discussed" or "based on the findings above".

Keep facts and guesses apart:
- Your own diagnosis or theory goes in as a labelled hypothesis, not as fact. After two failed fixes, give `architect`
  the symptoms and the failed attempts as data, not your conclusion.
- Briefing `code-grader` or any checker: never state the expected verdict or word the task so only PASS fits. Give the
  spec path and diff base, not your summary of what was done.
- When chaining (plan → `coder`, FAIL → `coder`), pass the upstream output verbatim and say what to do with it
  ("implement step 3 of this plan; flag any step that contradicts the code").

Say what to achieve, not how to search or edit. Don't tell a subagent to grep, sed or read specific files to find
code ("grep the repo for X"): that overrides its own tools, including the project's code-navigation MCPs. Name the
symbol or behaviour and let the subagent pick its tools.

Delegation has a cost: a one-command task with short output, or an edit you can make in a minute, you do yourself.

## After a subagent returns

- `architect`: check the plan against what the user asked for; surface open questions to the user.
- `coder`: read the `git diff` of its files before reporting success. Deviations or failures → fix yourself, re-brief,
  or escalate to `architect`.
- `code-grader`: never argue a FAIL away; fix it or show it to the user.
- Every report: handle the **Memory candidates** (write a note for them if they are
  worth keeping) and the **Friction** section (a tool, doc or command that misled a subagent): tell the user about
  anything that looks like a real problem. Subagents report; only the orchestrator writes memory.
- Summarize for the user; don't relay reports wholesale.

## Hand-off and commits

Before ending a turn with unfinished work: `memory/NOW.md` names what is being done and the exact next step (and the
gate status), and open items that are not next are in `memory/LATER.md`. Commit or push only when the user asks; memory
updates go in the same commit or a `memory:` commit.

**End of session:** when a task is finished, and before any push, follow the `memory-1` skill's end-of-session steps
once: write or supersede the notes, rewrite `NOW.md`, update the index, export the session archive, and run
`memory_check.py`. Do it before delegating a commit to `utility`; subagents never write memory. For an ordinary commit,
just bring `NOW.md` up to date. If the project has `docs/INDEX.md`, also update the docs that cover the changed code
(`docs-1`: `docs_index.py covers <file>`, then `write` and `check`). If the skills are missing, skip it.
