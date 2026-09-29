---
date: 2026-09-29
area: webnav
severity: wrong-result
status: open
---

**Call:** `selector(".gallery-item-media")`, `selector("#gallery-item-media")`
**Expected:** `web` root JS hits for `stage.querySelector<HTMLElement>("#gallery-item-media")` / `(".gallery-item-media.is-incoming")` (gallery-item.ts:140-141).
**Got:** missing in the `web` root (only the `[generated]` JS in `static` catches them, since `tsc` strips the type argument). 6 such call sites in `web/src` today (`querySelector<T>`, also `closest<T>`), e.g. `.gallery-item-thumb`/`-loading`/`-full`.
**Workaround:** grep, or read the `[generated]` hits.
**Idea:** `_JS_QUERY_RE` in `web_index.py:58` — allow an optional `<…>` type argument: `(?:querySelector(?:All)?|closest|matches)\s*(?:<[^>()]*>)?\(`. Add a positive test per API (per the earlier querySelector entry's idea).
