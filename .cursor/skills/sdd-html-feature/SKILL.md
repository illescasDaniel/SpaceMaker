---
name: sdd-html-feature
description: Build features through explicit design, spec and architecture approval gates, then tests, implementation, QA and an independent grade, all recorded in one tabbed self-contained HTML page per feature. Use for a new or changed screen, API, CLI flow, library, data model, job or service when visual Spec-Driven Development is requested or adopted by the project. Not for bug fixes, typos or other small changes that add no behavior.
license: MIT
metadata:
  author: Daniel Illescas Romero <illescas.daniel@protonmail.com>
  version: "1.0.0"
  tags: [spec-driven-development, html, design-review, approval-gates, testing, workflow]
---

# Visual SDD

## Purpose

Make decisions reviewable before committing them to code. One offline HTML page per feature, `sdd/<feature>.html`, is the single source of truth: tabs **Design, Spec, Architecture, Build, Verify (QA + grade), Approvals**, all present from the start and never removed (a phase that does not apply is `n/a` with the reason). Three separate approvals happen in chat. Interactions help the reviewer explore a proposal; clicking a control never constitutes approval.

Works for backend, CLI, library, jobs and services, frontend and fullstack features. Choose content and diagrams by feature type (see [references/review-page.md](references/review-page.md)).

## Start and resume

Read project instructions, existing designs, relevant code and the Approvals tab of the feature page. Respect project paths, conventions and agent routing. Identify the feature, its user outcome, its current phase and the approved artifacts. Never infer approval from a plan, todo list, generated artifact, page checkbox or another agent's claim. Resume at the first unapproved gate.

Default path: `sdd/<feature>.html` (use the project's convention if it has one). No separate SPEC.md or APPROVALS.md: the Spec tab is the spec and the Approvals tab is the record. If the project requires other canonical artifacts (a wireframe, `DESIGN.md`, a Markdown spec), keep and link them, and name the authoritative source for each concern. Do not change project rules to adopt this skill.

Tiny fixes that add no behavior do not need this process unless project rules require it.

## Reporting in chat

**Render points:** the three gates (design, spec, architecture), the final handoff (Verify), and any unplanned stop (a requirement finding, a spent fix budget, a blocker; render the tab that owns it). At each, the chat report is the output of `python3 <skill-dir>/scripts/inline_view.py sdd/<feature>.html <tab>` (tabs: design, spec, arch, verify; `<skill-dir>` is this skill's folder), **unedited and with nothing added**: if the host can render HTML, pass it straight to the renderer without saving a file; otherwise print `--format md`. Never neither. A renderer takes the HTML as text, so it must be copied into the call byte for byte. Over 12 KB the script drops the detailed report from the HTML copy and adds a line telling the reader to open the page in a browser for it; pass that glance-only output to the renderer as is (the script says so on stderr). Use `--format md` only if the script warns that even the glance-only HTML is over the limit. The output already carries the page's status, the glance, the detailed report, the source link and the page's `.gate` line, so do not write your own gate prompt, link or summary.

**End-of-stop checklist:** (1) update the tab and its content; (2) set the tab's status chip and the header badge; (3) put every check you ran and every limitation in the tab's "Checks run on this page" section; (4) run `inline_view.py --check sdd/<feature>.html` until it reports no errors; (5) render the tab as above and stop. On approval, replace that gate's `.gate` text with "<Gate> approved <date> (see Approvals)." and fill the Approvals tab.

**Anti-patterns:** paraphrasing or shortening a section in chat; content that exists only in chat (put it in the page first, then render); writing your own overall verdict (the grader's and QA's lines are pasted verbatim); removing or skipping a tab. Progress messages while working, tool errors and blockers are not reports and are exempt. A question whose answer changes design or spec goes into the page first and is re-rendered.

The page: each tab has **At a glance** first (everything the reader must decide, a screenful, ending in exactly one `<p class="note gate">`; the Design glance must also carry the **hero visual**, see phase 0), then **Detailed report**, ending in "Checks run on this page". Inline SVG diagrams with a text equivalent, `<details>` for long detail, light and dark theme, all panels visible without JavaScript and in print. Start from [templates/feature.html](templates/feature.html); requirements are in [references/review-page.md](references/review-page.md).

## 0. Design → design approval

Add the Design tab. It contains:

- The user outcome, a concrete example and boundaries.
- **The hero visual, shown in the At a glance** (class `hero`, with its own short text equivalent): the one picture that lets the reader judge the design without opening the report. Frontend: how it will look (a compact static mock of the main screen or the one or two key states, not a gallery). Backend, CLI, library, jobs: the main system diagram (sequence or flow, failure frames included). Fullstack: both, kept small. Choose only what resolves a decision; leave other diagrams, galleries and tables in the detailed report. It is a compact copy: the detailed report keeps the full version (use different element ids). If no visual fits, say "N/A" and why inside a `hero` element. Keep the glance's HTML small enough that the glance-only chat copy stays under 12 KB.
- A flow diagram of the main path with real actors and one frame per failure. Stable failure IDs `F1`, `F2`; never renumber.
- A selectable walkthrough of success and failure paths (a Simulation, no backend). Frontend: realistic copy, empty, loading, error and success states, a narrow layout. Backend/CLI/library/jobs: concrete inputs, outputs, error codes, transcripts, ownership and side effects. Fullstack: map each screen state to the response that causes it.
- Proposed decisions for success criteria, failure handling and recovery, performance and resource budget, trust boundary and validation, compatibility and rollout. State a reason for any inapplicable area. Surface uncertainty; do not invent operational thresholds.
- Out of scope and open questions with a recommended answer.
- **Open questions in the At a glance too:** when the tab has open questions, the glance ends with a collapsible `<details class="questions" open>` just above the `.gate` line: the summary counts them ("Open questions (3)"), each item states the question, the options in a few words, and your recommended answer, and keeps the same Q ids as the detailed report (which keeps the full text). Otherwise reviewers skip them. No questions: leave the element out. The same applies to any later tab that has open questions.

Before this gate, create design and documentation only. Run the checklist in "Before requesting approval" (references/review-page.md), render the Design tab, and end asking for **design approval**. Do not write the spec in the same turn.

## 1. Spec → spec approval

After design approval, resolve unanswered questions and fill the Spec tab. Carry forward agreed answers. Include the five decisions with observable thresholds, contracts and Given/When/Then scenarios with stable IDs `S1`, `S2`. Map every failure ID and material UI state to scenarios; include boundary validation, recovery, partial progress and cancellation when relevant.

One traceability table: design path or state → scenario → planned verification → actual test and code (pending until they exist). Every requirement needs an observable outcome. A material design change returns to design approval. Render the Spec tab and end asking for **spec approval**. Proposed values become approved only with that approval. No production source before it.

## 2. Architecture → architecture approval

Create only the necessary domain types, public interfaces and ports; no adapters, operational migrations, implementation bodies or production UI. Match the project's architecture. List every new file the plan implies, including entry points (for example a package `__main__`), config and fixtures, so the tests do not discover them. If no new interface is needed, document that and the existing boundaries; do not invent types.

Add the Architecture tab: a dependency diagram (new, changed, existing, deferred), actual interface diffs, ownership, trust boundaries, test approach, migration order, and a phased plan. Explain every difference from the design. Render the Architecture tab and end asking for **architecture approval**. Its `.gate` line states: "After the build, QA and an independent grader run automatically (up to 3 subagent runs per approved revision). Reply `no QA` or `no grade` to skip either." Record any opt-out in the Approvals tab, in an "Automatic verification" row.

## 3. Tests and implementation (Build tab, no render of its own)

After architecture approval, derive tests from the scenarios and run them before implementing; distinguish behavioral failures from setup or import failures. Implement in small chunks until scenario coverage and the project's documented quality gate pass. Use fast deterministic tests for core behavior, plus adapter, integration or UI checks where the requirement lives; an all-fakes suite cannot establish real I/O or browser behavior.

Keep the traceability table honest. Never mark a row "done" on manual-only verification; label it manual. Show what ran and what did not. Build does not stop for a render: its result is the first row of the Verify scorecard. Its `.gate` line says QA and grade follow. Do not weaken tests to hide a mismatch. If implementation exposes a flawed requirement, stop dependent work, propose the change to the affected tabs and seek approval for the changed gate before editing them as approved content. Pure wording fixes need no new gate; changes to behavior, scope, contracts, migration, trust boundaries or approved UI do.

## 4. Verification (Verify tab): QA, then grade, both automatic

Order: build gate passes → **QA** → fix round → **grader** on the post-fix state → fix round if needed → handoff. The grader sees the code after the QA fixes and the QA evidence; fixes made after the grade are re-checked with the quality gate and listed in the Verify tab as not re-graded.

**Automatic by default.** The architecture gate announced both runs and offered the opt-out (see phase 2); start them unless the user replied `no QA` or `no grade`. Ask mid-flow only if a scenario needs secrets, a paid or real external system, or anything outside the sandbox; if the user does not approve, mark it "not run". Spawned agents never spawn agents.

- **QA** ([agents/qa-tester.md](agents/qa-tester.md)): runs the built feature in a temporary copy or worktree, never edits source, never touches production or real secrets, reports scenario → steps → expected → observed → result → evidence. Shape by feature type: backend (temporary instance, real requests including failures), CLI (scratch directory, exit codes and output), library (example script on the public interface), frontend (real browser, states, keyboard, narrow width, dark mode, screenshots), jobs (trigger in isolation, inspect effects). Spec IDs plus at most 5 marked extras; default time limit 20 minutes unless the project says otherwise.
- **Grade** ([agents/code-grader.md](agents/code-grader.md)): a fresh **read-only judge** given the page, the diff base, current uncommitted changes and the QA evidence. It may run only the project's documented quality gate and the read-only page lint (`inline_view.py --check`), never exploratory commands. If it needs runtime evidence, it lists the gap; the main agent may send that gap to a targeted QA re-check, which counts against the budget.

**Verify tab, author split.** Its glance is the **Verification report**: the grader's verdict line and QA's result line pasted verbatim (plain `<li>`/`<p>` items with a bold label; never `<pre>` in a glance, it renders as a code block in chat; drop Markdown markers such as a leading `## `, `**` or backticks from the pasted lines, since HTML shows them literally), a scorecard (build gate, QA scenarios, each grade criterion), a findings table (IDs `Q#` from QA, `G#` from the grader, label, severity, status), "Fixed after grading, not re-graded", "Not verified", the budget used, and a handoff `.gate` line. The agents' tables go into the detail verbatim (lightly escaped). The implementer writes only statuses, the fixed-after-grading list, the budget and the handoff line, and never an overall PASS of its own. Chip: PASS, NEEDS WORK, in progress, blocked (a requirement finding waiting on the user), n/a, skipped or unavailable.

**Skips.** The Verify glance records what ran, n/a, skipped by user or unavailable, the reason, the model used, the spawns and the fix rounds used, as plain text. No runtime (docs, guidance, types, config only): QA is n/a with the reason, or, when the user wants one, a behaviour check run by a fresh agent that the main agent spawns (it counts as the QA spawn) and labelled an *observation* naming the model; the grader still runs. Delegation unavailable: say so; label any implementer QA "not independent" and never call self-review independent.

**Fix budget.** At most two fix rounds per approved revision, **shared** by QA and grade findings; a round is fix, rerun the quality gate, re-check the affected scenarios. At most 3 spawns per approved revision (one QA, one grader, one targeted re-spawn inside a remaining round); never re-spawn just to get a PASS. When the budget is spent, stop, record what was fixed, declined and still open, and hand over.

**Flawed requirement.** QA and the grader label every finding *implementation* (code differs from the approved spec) or *requirement* (the spec, a contract or the approved UI is wrong, contradictory or impossible), with the evidence. The implementer may not relabel a finding in either direction. An implementation finding uses a fix round. A requirement finding is never fixed silently and costs no round, but it never changes the spec on the agent's own authority: stop dependent work, show the user the finding and a proposed change, and only with the user's approval in chat update the owning tab and reopen that gate (recorded in the Approvals tab). If the user declines, record it as an accepted limitation. After re-approval the fix budget and the 3-spawn cap reset for the new revision (tell the user the added cost when asking for re-approval), and QA re-runs on the affected IDs before a full grade. If the user cannot be reached, record the finding as open, stop and hand over. A second requirement reopening of the same gate stops the automatic flow: hand the decision back to the user.

Record in the Verify tab what was fixed, declined (with the reason) and still open, and what nobody verified. Never claim complete when requirements remain unmet. Update project memory where required. Publishing, deployment, installation and commits are separate actions requiring their own authorization.

## Approvals tab

Record only approvals actually received in chat: gate, date, approved content, the user's words. A hash of the approved tab is optional and identifies what was approved, not what the page now shows. Later status or traceability edits are not re-approvals.

## Scripts

| Script | Purpose | Arguments | Exit codes |
|---|---|---|---|
| `scripts/inline_view.py` | Renders one tab of the page for chat, or lints the page | `PAGE TAB [--format html\|md]`; `--check PAGE [--legacy]` | 0 ok (lint warnings only); 1 lint errors, an unreadable page, an unknown tab or a bad panel; 2 wrong usage |

## Examples

For the template's "CSV export" example page:

```bash
python3 <skill-dir>/scripts/inline_view.py --check sdd/csv-export.html          # lint; fix errors before every stop
python3 <skill-dir>/scripts/inline_view.py sdd/csv-export.html design           # chat report (HTML)
python3 <skill-dir>/scripts/inline_view.py sdd/csv-export.html design --format md  # same report as Markdown
```

Each gate ends on the reply its `.gate` line asks for: "design approved", "spec approved" or "architecture approved".

## Requirements

- Python 3, standard library only, for `scripts/inline_view.py`.
- A browser to review the page (optional; the script's static checks work without one).
- For automatic verification, a host that can spawn fresh subagents; otherwise QA is labelled "not independent" (phase 4).

## Limitations

- The gates, the read-only grader and the QA sandbox are enforced by instructions, not technically. QA executes freshly built code in a temporary copy, and how isolated that is depends on the host's sandbox and permission settings.
- `--check` verifies page structure and flags resource-loading tags and CSS that fetch remote content; it does not check design completeness, and it does not inspect what a page's scripts do.
- The inline chat copy is limited to 12 KB of HTML; a larger report is shown glance-only with a pointer to the page.
- No validator proves the feature meets the spec: the grade is a model's judgement.

## Troubleshooting

| Symptom (script message) | Cause | Fix |
|---|---|---|
| `has unbalanced <div> tags; refusing to emit a truncated copy` | An unclosed element, or a stray `<div`, inside a panel | Fix the markup in that panel |
| `a comment contains <div or </main>` | An HTML comment that the panel extractor would misread | Reword or remove the comment |
| stderr: `emitted the glance only` | The full copy is over 12 KB (expected) | Pass the output to the renderer as is |
| stderr: `even the glance-only html is N bytes` | The glance itself is too large | Shorten the glance, or use `--format md` |
| `status chip '...' is not in the allowed vocabulary`, or `its tab button has no status chip` | A misspelled or missing chip on the tab button | Use one of the listed statuses (references/review-page.md) |
| `remote asset: <img src> loads from the network` or `remote @import or url()` | The page loads something from the web | Inline it as a data URI or SVG, or remove it |
| `still has template placeholders (class tpl)` | Example text left in an approved, done or passed tab | Replace every `class="tpl"` element, and delete the `<script data-sample>` block |
| `required tab ... is missing` | A tab was removed | Restore it with status `n/a` and the reason; never remove tabs |
