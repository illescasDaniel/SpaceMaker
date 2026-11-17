# Feature page requirements

One UTF-8 HTML file per feature, `sdd/<feature>.html` by default (use the project's own convention if it has one). It is the single source of truth for every phase. Start from [../templates/feature.html](../templates/feature.html) and replace the example content.

The template carries no authoring comments in its panels; the rules live here. Replace its example text (marked `class="tpl"`), keep the structural `<!-- === TAB === -->` banners, and run `inline_view.py --check` before ending a stop.

## Tabs and the summary-first format

Tabs: **Design, Spec, Architecture, Build, Verify, Approvals**. All exist from the start and are never removed; a phase that does not apply is `n/a` with the reason in its glance. Each status chip uses only: approved, awaiting approval, not started, in progress, blocked (a requirement finding waiting on the user), done, n/a, skipped, unavailable (Verify also PASS or NEEDS WORK; Approvals counts gates, for example "0 of 3 gates"). The header badge states the current gate. Pages from older versions have QA and Grade tabs instead of Verify; the script still renders them (`verify` returns both) and `--check` only warns.

Every tab except Approvals (a plain record table) has the same shape:

1. **At a glance** (first): a screenful with everything the reader must decide or know: what changes, the failure paths, decisions to settle, what is not verified. **The Design glance leads with the hero visual** (`<div class="hero">`): the compact mock of how a frontend will look, or the main system diagram of a backend, CLI, library or job (both for fullstack), with a short "Text equivalent" paragraph. The hero is a compact copy: the detailed report keeps the full version, with different element ids. Only the good, deciding visuals go there; everything else stays in the detail. Other tabs may add a hero when a picture decides more than words (Architecture: the dependency diagram). **Open questions go in the glance too**, as a collapsible `<details class="questions" open>` just above the `.gate` line (summary with the count; each item: question, options in a few words, recommended answer, same Q id as in the detail). Omit it when there are none. It ends in exactly one `<p class="note gate">` holding the exact chat reply for the next gate (or the handoff line). After approval its text becomes "<Gate> approved <date> (see Approvals)." so the line can always be found.
2. **Detailed report** (`<h2 class="rep">`): all the detail, containing everything in the glance and more, never different content. Spec tab: full Given/When/Then for every scenario (in `<details class="gwt">`), the contracts, and the traceability table. Every detailed report ends with a **Checks run on this page** section: mechanical checks, browser checks that ran, and limitations. Chat never carries content that is not in the page.

**Verify tab.** Glance = the Verification report: grader verdict line and QA result line pasted verbatim (as `<li>` or `<p>` items with a bold source label, never `<pre>`: a glance `<pre>` renders as a code block in chat; `--check` warns; strip Markdown markers like a leading `## `, `**` or backticks, as HTML shows them literally), scorecard (build gate, QA scenarios, each grade criterion), findings table with `Q#`/`G#` IDs, label, severity and status, "Fixed after grading, not re-graded", "Not verified", budget used, and a handoff `.gate`. Detail: QA scenario runs, then the grader's criteria, scenario map and findings, pasted from the agents' reports. The implementer writes only statuses, the fixed-after-grading list, the budget and the handoff line, and never an overall PASS of its own. Placeholder text carries `class="tpl"`; `--check` fails if any remains in a done or approved tab.

Tabs use ARIA `tablist`, `tab` and `tabpanel`, arrow keys, Home and End, and `#hash` links. Without JavaScript all panels are visible. Print shows every panel; `details` are opened by the `beforeprint` script and, where the browser supports it, by a `::details-content` rule in the print stylesheet.

## Content by feature type

Pick what resolves a decision; mark a view "N/A — reason" when it does not apply.

- **Backend or API:** sequence diagram with real actors and F-frames; request/response examples; status and error codes; state after each failure; data model or lifecycle if it resolves a decision.
- **CLI:** transcripts of success and each failure, exit codes, help text, flags and defaults.
- **Library:** usage snippet, public interface and errors, dependency direction.
- **Jobs and services:** trigger, schedule, retry and idempotence, lifecycle (states and transitions), side effects.
- **Frontend:** realistic copy; every state (empty, loading, error, success) as a gallery; a narrow layout; map each screen state to the response or event causing it.
- **Docs or guidance only:** show before and after text, what changes in behavior, and how it will be checked.

## Diagrams

Inline SVG only, 3–7 named nodes per diagram, with `<title>`, `<desc>`, `aria-labelledby` and a text equivalent under it. A diagram answers one question (for example "where is input validated?"). Use stable IDs (F1, S1). Colour is never the only signal: nodes carry a text tag (NEW, CHANGED, EXISTING, DEFERRED; sequence-diagram headers may use "· added" or "· existing" instead) and a distinct line style (thick = changed, dashed = deferred or failure). Diagrams shown in the template: sequence with failure frames, dependency graph with legend. Others to use when helpful: lifecycle/state, data model, contract/seam. Markers use `fill="context-stroke"` so they follow the line colour.

Do not use Mermaid in a page that would need a CDN. If the project mandates Mermaid source, keep it in the project's design file and reproduce a simplified diagram here.

## Theme and accessibility

Define colours as `:root` tokens; override them in `@media screen and (prefers-color-scheme:dark)`. Use `color-mix` for tints. Keep text contrast adequate in both themes, visible focus outlines, and a narrow layout that needs no horizontal scrolling at 320 px (tables scroll locally in a focusable region). Tables with five or more prose columns (QA runs, failures) use `<table class="cards">` with a `data-label` on each `<td>`; the template CSS turns each row into a labelled card below 600 px (the inline chat frame included), so nothing scrolls sideways and no column has to be dropped. Wrap each SVG in a focusable `.scroll` region with a minimum width on narrow screens so labels stay legible. Do not disable zoom. Announce changed summaries with a small polite live region. Data-driven labels use `textContent`, never `innerHTML`.

Reviewer notes say "Review only"; mock content says "Simulation". No "Approve" button that implies workflow authorization.

## Inline render in chat

At each render point (the three gates, the handoff, unplanned stops) the chat report is generated from the page, never retyped: `python3 <skill-dir>/scripts/inline_view.py sdd/<feature>.html <tab>` (design, spec, arch, verify, appr), where `<skill-dir>` is the skill's folder. The HTML output starts with one line holding the header badge and the tab's status chip, then the **At a glance** content open, the detailed report in one `<details class="big">`, and a `Source: page#p-tab` footer. Pass it straight to the host's renderer (do not save it in the project); above 12 KB the script leaves the detailed report out of the HTML copy (a long copy can drift, because the renderer takes the HTML as text) and shows a line telling the reader to open the page in a browser for it; it says so on stderr. Only if even that glance-only copy is over 12 KB does it warn, and then `--format md` is used. A host that cannot render HTML gets `--format md`: the glance as Markdown, the report anchor, and the `.gate` line verbatim last. One of the two is always used; add nothing to it. Mark elements to omit from the inline copy with class `skip-inline` on a `<p>` or `<nav>`. Each panel must open exactly as `<div role="tabpanel" id="p-<tab>" …>` (that attribute order) and may not contain `<div` or `</main>` inside a comment; the script refuses to emit a panel whose `<div>` tags do not balance. The inline version uses transparent body and the host's theme variables with fallbacks. Never claim an inline preview that did not happen.

## Approvals tab

Record only approvals actually received in chat: gate, date, approved content (a short hash of the tab content is optional, but note it identifies what was approved, not what the page shows today), and the user's words. Later edits to status labels and traceability are not re-approvals; a behaviour, scope or contract change reopens the gate that owns it.

## Before requesting approval

0. Run `python3 <skill-dir>/scripts/inline_view.py --check sdd/<feature>.html` and fix every error (tabs, glance, one `.gate`, balanced panels, status vocabulary, no placeholders in finished tabs, no remote assets).
1. Open the saved file with networking disabled when browser tools exist. Exercise tabs, selectors, disclosures, links, keyboard use, a narrow viewport, dark mode and print; check the console.
2. Check every relative link. Check each diagram has a text equivalent. Check every failure ID appears in the failure inventory and in the traceability table.
3. Confirm there are no remote assets, live calls, secrets or untrusted HTML.
4. Without browser tooling, inspect statically and say which visual and interaction checks did not run.
5. Write the results of steps 0 to 4, and every limitation, into the tab's "Checks run on this page" section. The render shows them and prints the link; do not repeat them in chat.

No validator can establish design completeness. Report mechanical checks separately from human review and actual browser checks, in that section.
