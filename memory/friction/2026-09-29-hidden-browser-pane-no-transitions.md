---
date: 2026-09-29
area: tooling
severity: confusing
status: open
---

**Call:** `javascript_tool` timing checks of a CSS transition in the Browser pane after `preview_start`.
**Got:** computed opacity stayed `1` for the whole transition; looked like the animation was broken. `document.visibilityState` was `hidden` — hidden panes don't render, so CSS transitions/animations never advance (transitionend also fires late).
**Workaround:** `tabs_select` + a `computer` screenshot (makes the page `visible`), then re-run.
**Idea:** for animation checks, log `document.visibilityState` in the same script; note this in the agent docs.
