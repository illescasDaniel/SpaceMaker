# Spec-Driven Development

Before implementing a user-facing feature or changing behavior:

1. Create or update `wireframes/<screen>.html` for new/changed UI. **Stop and obtain explicit human UX/design approval in chat** before any spec or `src/` work.
2. Read or create `specs/<feature>/SPEC.md` with BDD acceptance criteria and out-of-scope items. **Stop and obtain explicit human spec approval in chat** before domain, ports, adapters, or production static UI.
3. Architecture (domain + ports): stop for explicit approval before tests and implementation.
4. Write tests from the BDD scenarios before implementation (Phase 4).
5. If implementation reveals a spec gap, update the spec (and wireframe if layout changed), **get re-approval**, then continue — do not silently change behavior.

**Never** treat an attached plan, plan-mode OK, a todo list, "implement the plan", or "complete all todos" as substituting for wireframe or spec approval unless the user explicitly approves those artifacts **in chat** (e.g. "wireframe approved", "spec approved").

After plan approval, the **first** execution turn is **wireframe only**, then **stop** — give the user time to review in a browser before specs or `src/`.

**One phase per explicit approval.** Do not batch wireframe + spec + implementation in one run.

New features require wireframe + spec + tests + implementation. Refactors must keep existing specs green or update specs explicitly.
