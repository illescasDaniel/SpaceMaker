# UI motion (native-feel transitions)

## Metadata

- **Feature:** A shared, minimal motion vocabulary applied across the desktop shell and phone web pages so interactions ease instead of snapping instantly.
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html), [wireframes/phone-upload.html](../../wireframes/phone-upload.html), [wireframes/phone-receive.html](../../wireframes/phone-receive.html), [wireframes/phone-share.html](../../wireframes/phone-share.html) — motion demonstrated live via real CSS transitions/animations in each file, plus a "Motion notes" line in each banner. **Wireframe approved** 2026-09-25.
- **Related:** [home-modules](../home-modules/SPEC.md) (screen routing this applies motion to), [gallery](../gallery/SPEC.md) (timeline/item add-remove this applies motion to), [easy-mode](../easy-mode/SPEC.md), [main-wizard](../main-wizard/SPEC.md), [receive-files](../receive-files/SPEC.md), [send-files](../send-files/SPEC.md)

## Problem & scope

The desktop app and phone web pages currently have zero motion — every screen switch, hover, press, and list change happens with a hard, instant snap, which reads as "a website" rather than a native desktop app. This spec adds a small, consistent set of transitions/animations across existing screens. It does **not** change any layout, add new screens, or change any behavior — purely additive motion on top of already-approved UI.

## Motion vocabulary

Defined once as CSS custom properties (in `theme.css` for desktop/mobile-gallery shells, and inline in each phone page's `<style>`):

| Token | Value | Use |
|---|---|---|
| `--ease-standard` | `cubic-bezier(0.2, 0, 0, 1)` | All transitions/animations in this spec |
| `--dur-fast` | `120ms` | Hover/press feedback, tab/toggle/chip state changes |
| `--dur-base` | `200ms` | Screen/panel navigation, list item add/remove, async state swaps |

A `prefers-reduced-motion: reduce` media query collapses all `transition-duration` / `animation-duration` to near-zero globally. This is a real OS-level accessibility setting; SpaceMaker respects it like any native app would.

## What gets motion

Only state changes the user directly causes. No page-load intro animations, no decorative or looping animation, no motion added to elements that don't already change state.

- **Screen navigation** (desktop shell `index.html` / wireframe `app.html`): switching between Home hub, module screens (Photo backup, USB photo backup, Receive files, Send files), the Advanced wizard, and Gallery cross-fades with a slight upward settle instead of a hard cut.
- **Gallery item detail** (`gallery` item page, see [gallery](../gallery/SPEC.md) "Item page" / "Progressive preview loading"): opening an item scales up slightly and fades in — a distinct, more "photo-opening" entrance than the generic screen cross-fade above, since it's the one navigation that replaces a grid with a single focused piece of media. **Previous**/**Next** slides the preview out and the adjacent one in from the corresponding side, instead of swapping instantly. While the full-size preview loads (initial open or after a Previous/Next step), the item's existing thumbnail fills the frame immediately and cross-fades to the full preview once it loads, with a loading spinner over it in the meantime.
- **Wizard steps** (`main-wizard`): a step card's active/done state (numbered badge, opacity when disabled) eases instead of snapping.
- **Hover/press feedback:** buttons (`.btn` and variants), chips, view tabs, toggle groups, connection-method toggle, module tiles, gallery item prev/next controls, and phone-page buttons ease their background/border/color on hover and scale down slightly on press.
- **List add/remove** (`gallery` timeline): a thumbnail being removed (e.g. after delete) fades and shrinks out before it's removed from the DOM, instead of popping out of the grid instantly.
- **Async state swaps:** progress bar fill width eases as it updates; info panels (connection help, gallery phone-QR popup) fade in when shown; phone-page state panels (Ready/Uploading/Paused, file list/expired) fade in when swapped.

## Out of scope

- Page-load intro animations (first paint of any screen).
- Decorative or looping animation unrelated to a real wait state — e.g. the infinite-scroll "Loading more…" spinner keeps its existing appearance, unaffected by this spec. The gallery item preview's loading spinner is the one exception: it's the visual counterpart to the thumbnail→full-preview progressive load this spec adds (see "Gallery item detail" above and [gallery](../gallery/SPEC.md)), so it is in scope.
- Motion on elements whose state doesn't change (e.g. static text, disabled decorative icons).
- Any new screens, layout changes, or behavior changes — this spec only adds `transition`/`animation` CSS and, where a snap-remove needs a moment to play (gallery thumbnail removal), a short deferred DOM removal in JS.
- Gesture-driven motion (swipe-to-dismiss, drag reordering) — no such interactions exist today.

## Acceptance criteria (BDD)

### Scenario: Navigating between screens cross-fades

- **Given** the user is on the Home hub
- **When** they open a module screen, the wizard, or Gallery
- **Then** the new screen fades and settles in over `--dur-base` (200ms)
- **And** the previous screen does not remain visible or flash

### Scenario: Button press gives immediate visual feedback

- **Given** any primary/secondary/ghost button, chip, or toggle control
- **When** the user presses it
- **Then** it visibly eases (background/border/color and a slight scale) within `--dur-fast` (120ms)
- **And** the eased state reverts on release without a jump

### Scenario: Module tile hover feedback

- **Given** the Home hub is shown
- **When** the user hovers a module tile
- **Then** the tile border and elevation ease in over `--dur-fast`
- **And** pressing it scales down slightly before navigating

### Scenario: Gallery item opens like a photo, not a page

- **Given** the user is viewing the gallery grid
- **When** they open an item's detail page
- **Then** the item page scales up from slightly smaller and fades in, distinct from the generic screen cross-fade
- **And** the grid does not remain visible or flash underneath it

### Scenario: Previous/Next slides the preview

- **Given** the gallery item page for an item with an adjacent item in the chosen direction
- **When** the user chooses **Previous** or **Next**
- **Then** the current preview slides and fades out toward that direction
- **And** the adjacent item's preview slides and fades in from the opposite side

### Scenario: Preview loading shows the thumbnail first

- **Given** the gallery item page is opening, or has just stepped to an adjacent item
- **When** the full-size preview has not finished loading
- **Then** the item's existing thumbnail fills the preview area immediately, with a spinner over it
- **And** once the full-size preview loads, it cross-fades in over the thumbnail and the spinner fades out
- **And** the preview area's size does not change at any point in this sequence

### Scenario: Gallery thumbnail removal animates out

- **Given** the gallery timeline shows at least one thumbnail
- **When** an item is removed (e.g. after Delete)
- **Then** that thumbnail fades and shrinks over `--dur-base` before leaving the grid
- **And** the remaining thumbnails reflow into its place without a hard jump

### Scenario: Progress and panel state changes ease

- **Given** a progress bar or an info/QR popup panel
- **When** its value updates or it is shown/hidden
- **Then** the width change or show/hide is eased rather than instant

### Scenario: Reduced motion is respected

- **Given** the OS/browser reports `prefers-reduced-motion: reduce`
- **When** any of the above interactions occur
- **Then** all transitions and animations complete near-instantly (no perceptible motion)
- **And** the gallery item preview's loading spinner shows as a static ring instead of continuously rotating

### Scenario: No motion added to inert elements

- **Given** a static element whose state never changes (e.g. plain body text, a disabled decorative icon)
- **When** the surrounding UI is otherwise animating
- **Then** that element has no `transition`/`animation` applied to it

## Testing strategy

Purely presentational CSS/JS in `adapters/inbound/web/static/` — no domain or application logic, so no `tests/unit/` pytest coverage applies. Verification is:

- **Biome** (`npm run check`) lints the touched HTML/JS/CSS for syntax and style.
- **Manual/visual QA** in the browser: exercise each scenario above (navigation, hover/press, thumbnail removal, panel/progress swaps) and confirm against the approved wireframes; toggle `prefers-reduced-motion` in devtools and re-confirm motion collapses to near-instant.

## Out-of-scope test coverage

- Automated visual regression / motion timing assertions (no such harness exists in this repo; would require a browser automation layer beyond current test infra).
