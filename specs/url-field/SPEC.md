# URL field with Copy button and working info (ⓘ) buttons

## Metadata

- **Feature:** (1) One shared **URL field** (read-only single-line input that scrolls horizontally + small icon **Copy** button) for every phone/gallery URL on the desktop UI; (2) every **ⓘ info button** opens and closes its panel; (3) the USB photo backup **Visualize** step and the gallery **On your phone** popup use the URL field instead of an overflowing text box.
- **Use cases:** none (frontend-only; no ports or domain change)
- **Wireframe:** [wireframes/url-field.html](../../wireframes/url-field.html) — sections A (phone popup), B (ⓘ panels), C (USB Visualize), D (narrow width). **Wireframe approved** 2026-10-18 (chat).
- **Design decisions approved:** 2026-10-18 (chat)
- **Spec approved:** 2026-10-18 (chat); copy-order amendment (execCommand first, because of the pywebview Qt permission bug) approved 2026-10-18 (chat)
- **Related:** [gallery](../gallery/SPEC.md) (LAN URL + QR), [easy-mode](../easy-mode/SPEC.md), [main-wizard](../main-wizard/SPEC.md), [receive-files](../receive-files/SPEC.md), [send-files](../send-files/SPEC.md), [transfer-files](../transfer-files/SPEC.md), [network-passcode](../network-passcode/SPEC.md), [ui-motion](../ui-motion/SPEC.md)
- **Reported against:** AppImage 1.1.0 (gallery URL overflowing its popup; ⓘ buttons on Photo backup etc. doing nothing; USB Visualize URL stretching across the card).

## Design decisions

### Success criteria

- Every ⓘ button in the desktop UI (`index.html`) opens and closes its panel on click; `aria-expanded` (button) and `aria-hidden` (panel) always agree with the visible state. A unit test lists every `info-btn` id in `index.html` and fails if one has no binding or no matching panel, so a dead ⓘ cannot ship again.
- Every phone/gallery URL shown on the desktop UI is rendered by the **same** URL field component: one line, horizontally scrollable, plus a Copy button. The surrounding card never grows wider or overflows because of the URL, at any width down to the narrow check in the wireframe (~340 px).
- The gallery popup, the USB Visualize step and the six QR info panels (Photo backup, Receive, Send, Transfer, USB Wi‑Fi) all look and behave identically.
- Copy shows **Copied** only after the text really reached the clipboard.

### Failure handling

- Copy tries select + `document.execCommand('copy')` **first**; only if that returns false does it use `navigator.clipboard.writeText`, and only in a secure context. Reason (found in AppImage testing, 2026-10-18): in the desktop webview `navigator.clipboard` makes QtWebEngine raise a permission request that pywebview's Qt backend answers with an invalid type (`TypeError` in `onFeaturePermissionRequested`), so the copy fails; `execCommand` needs no permission. The phone gallery is plain `http://` on the LAN (no `navigator.clipboard` at all), so this path is the normal one.
- If both fail: no **Copied**; the URL stays selected so the user can press Ctrl/Cmd+C.
- URL not known yet (server/session not started, no LAN IP): the field is empty and the Copy button is disabled. No `…` placeholder text.
- A missing ⓘ button or panel element is a silent no-op (same as today); the id-coverage test catches it in CI instead.

### Performance & resource budget

- Frontend-only: no new endpoint, request, dependency or timer except the ~1.5 s **Copied** reset.
- One shared helper replaces the two existing toggle styles (`bindDisclosure` using `hidden`, and the inline `.visible` handlers); no per-panel code.
- Panel fade and **Copied** swap use existing `--dur-*` motion tokens and are disabled under `prefers-reduced-motion` ([ui-motion](../ui-motion/SPEC.md)).

### Trust boundary

- The URL comes from our own backend (it can contain the access key `#k=…` / `?t=…`); it is not user-entered. It is written with `input.value`, never `innerHTML`.
- Copy writes to the local clipboard only, only on an explicit click, never automatically, and sends nothing over the network.
- Out of scope: how URLs or keys are generated, the phone-side pages and the unlock flow.

## Triggers & routing

- **Entry:** desktop webview `index.html` (Home modules, USB photo backup wizard, Gallery tab phone popup). No new routes.
- The gallery standalone phone page (`gallery_mobile.html`) does not show a URL field; unchanged.

## Visual & UI rules

- **URL field** (`.url-field`): `<input type="text" readonly>` (flex, `min-width: 0`) + `.url-copy` icon button (copy icon, `aria-label="Copy URL"`, tooltip "Copy URL"). Single line, no wrapping, no ellipsis; the user scrolls or focuses to see the rest. Focus/click selects all text.
- **Copied** state: the icon swaps for the text "Copied" in the success colour for ~1.5 s, announced via `aria-live="polite"`, then reverts.
- **ⓘ button** (`.info-btn`): unchanged circle; when its panel is open it uses the filled style (`aria-expanded="true"`). Panel opens inline directly below its row. **Escape** closes the open panel and returns focus to its button.
- **Gallery popup "On your phone":** title, close button, hint, QR, URL field, note "Please don't open this while uploading content." (wireframe A).
- **USB Visualize step:** QR with the URL field beside it (wrapping under it on narrow cards); the firewall ⓘ panel opens below the QR block, full card width (wireframe C).
- **QR info panels:** keep their text, replace the bare input with the URL field (wireframe B).
- Wireframe-only notes (Review only / Agent note) do not ship.

## Acceptance criteria

### Scenario: Info button toggles its panel

**Given** the Photo backup screen **When** the user clicks the QR ⓘ **Then** its panel becomes visible, the button has `aria-expanded="true"` and the panel `aria-hidden="false"`; clicking again hides it and reverses both.

### Scenario: Every info button is wired

**Given** each ⓘ button listed in `index.html` (easy-qr, easy-compress, receive-qr, send-qr, transfer-qr, wifi-qr, connection, firewall, passcode, USB folders/dest/mode/actions) **When** the bindings are set up **Then** every one has a matching panel and a click toggles it (no dead ⓘ).

### Scenario: Escape closes the open panel

**Given** an open ⓘ panel with focus inside the page **When** the user presses Escape **Then** the panel closes and its ⓘ button has focus.

### Scenario: Long URL stays on one line

**Given** a gallery URL with a very long key **When** shown in the popup or the USB Visualize step **Then** it is in a single-line read-only input, the card keeps its width and the user can scroll the text horizontally.

### Scenario: Copy with execCommand (no clipboard permission)

**Given** a URL field with a known URL **When** the user clicks Copy and `execCommand('copy')` succeeds **Then** the clipboard contains exactly the URL, `navigator.clipboard` is never touched, and the button shows **Copied** for about 1.5 s.

### Scenario: Copy falls back to the clipboard api

**Given** `execCommand('copy')` returns false **When** the user clicks Copy **Then** `navigator.clipboard.writeText` is tried only in a secure context (never on plain `http://` LAN pages) and **Copied** is shown only if it succeeded.

### Scenario: Both copy methods fail

**Given** both clipboard methods fail **When** the user clicks Copy **Then** no **Copied** appears and the URL text stays selected.

### Scenario: URL not known yet

**Given** the URL is not known yet **When** the field is rendered **Then** the input is empty and the Copy button is disabled; once the URL is set the button is enabled.

### Scenario: Markup characters stay plain text

**Given** a URL that contains characters such as `<` or `"` **When** it is rendered **Then** it appears as plain text in the input (no markup is interpreted).

### Scenario: USB Visualize and popup use the URL field

**Given** the USB photo backup Visualize step with the gallery ready **When** it is shown **Then** the URL appears in the URL field beside the QR, not as a wide plain box (and the same helper renders the gallery popup URL).

### Scenario: Reduced motion

**Given** `prefers-reduced-motion: reduce` **When** a panel opens or **Copied** appears **Then** no animation runs.

## Out of scope

- New info content or rewording of existing ⓘ text.
- Changing how URLs, QR codes, keys or passcodes are generated.
- Phone-side pages (`upload.html`, `receive.html`, `share.html`, `transfer.html`, `unlock.html`, `gallery_mobile.html`).
- A "share" sheet or QR-from-URL tooling.
