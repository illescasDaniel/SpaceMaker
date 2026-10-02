# Network passcode (LAN access control)

## Metadata

- **Feature:** Optional passcode that other devices on the network must supply before using any SpaceMaker page or API
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — `#passcode-dock` inside `#view-home`; phone [wireframes/phone-unlock.html](../../wireframes/phone-unlock.html). **Wireframe approved** 2026-10-02.
- **Design decisions approved:** 2026-10-02 (chat)
- **Spec approved:** 2026-10-02
- **Related:** [gallery](../gallery/SPEC.md), [home-modules](../home-modules/SPEC.md), [easy-mode](../easy-mode/SPEC.md), [receive-files](../receive-files/SPEC.md), [send-files](../send-files/SPEC.md), [transfer-files](../transfer-files/SPEC.md)

## Design decisions

### Success criteria

- With no passcode set (the default) behaviour is identical to today.
- With a passcode set, every non-loopback HTTP and WebSocket request is rejected with 401 unless it carries a valid login. Exempt (exact paths only): `/api/unlock`, `/favicon.ico`, `/static/unlock.css` and `/static/js/unlock.js` (the unlock page itself is served by the 401 response).
- Scanning any SpaceMaker QR signs a phone in without typing; the login survives page loads and desktop app restarts.
- Setting, changing or clearing the passcode takes effect immediately and signs out every other device. The desktop (loopback) never asks.
- The feature never reads or modifies library or transferred files.
- This is **access control, not encryption**: AES / transport encryption is explicitly out of scope (see Out of scope).

### Failure handling

- Wrong passcode → 401 and the phone page shows "Wrong passcode. Try again." After 5 consecutive wrong tries from one IP: lockout of 30 s, doubling on each further lockout up to 15 min; during lockout the phone shows "Too many attempts. Try again in N seconds." and the attempt is not evaluated.
- Invalid or stale login (for example passcode changed) → unlock page for navigations, 401 JSON for API calls (the page then redirects to unlock).
- Unreadable or corrupt stored hash/secret → app starts with the passcode cleared and Home shows a warning; it never fails open silently without telling the user.
- Passcode shorter than 4 characters is rejected on the desktop with an inline message; nothing is stored.

### Performance & resource budget

- Login verification is a constant-time HMAC comparison with no disk I/O: < 1 ms added per request (video range requests unaffected).
- scrypt runs only on set and on unlock attempts (~100 ms), off the event loop.
- Lockout table is in memory, capped at 1,000 IPs (oldest evicted). No new dependencies, no network cost.

### Trust boundary

- Untrusted: all non-loopback clients — headers, cookies, query strings, the typed passcode, the QR token.
- Trusted: loopback requests (desktop UI), as today.
- Enforced in **one** inbound middleware plus the WebSocket guard, not per route; a new route is protected by default.
- Stored in settings: salted scrypt hash and a random token secret only; the plaintext passcode is never stored or logged. Compared with `hmac.compare_digest`.
- Cookie `HttpOnly`, `SameSite=Strict`, no expiry; valid until the token secret is rotated (set / change / clear).
- QR token travels in the URL fragment (`#k=…`), never sent to the server in a request line, so it stays out of logs; the unlock page script exchanges it via `POST /api/unlock`.
- Limit stated to users: plain HTTP means a network sniffer can read the passcode or cookie.

## Triggers & routing

- Desktop: Home shows the **Network passcode** dock bottom-left. `PUT /api/network-passcode` (loopback only) sets or changes; `DELETE /api/network-passcode` clears; `GET /api/network-passcode` returns `{ "enabled": bool }` (never the hash).
- Non-loopback requests while enabled: middleware checks the login cookie. Missing/invalid → `GET` navigations receive the unlock page (status 401, `/unlock` HTML); everything else receives `401 {"detail": "passcode-required"}`. WebSocket `/ws` stays loopback-only.
- `POST /api/unlock` (non-loopback, rate-limited) accepts either `{ "passcode": "…" }` or `{ "token": "…" }`; success sets the login cookie.
- QR/URL builders append `#k=<token>` to the phone URLs only while a passcode is enabled (Photo backup, Receive, Send, Transfer, Gallery QR).
- Rotating the token secret (set, change, clear) invalidates all cookies and previously shown QR tokens.

## Visual & UI rules

- Dock: fixed bottom-left, 16.5 rem wide; full width on windows ≤ 640 px; Home only. Title with lock icon and **i** button; help panel opens above the field.
- **Open state:** password input "Choose a passcode", **Set**, warning line "Not set — anyone on your Wi-Fi can open the Gallery."
- **Active state:** read-only `••••••••`, **Change** (returns to input with placeholder "New passcode"), **Clear**; line "Active" The passcode is never shown again.
- Info panel states: other devices must enter it; this computer never asks; QR scan signs in; remembered between launches (hash only), change/clear signs everyone out; **Not encryption** note.
- Phone unlock page: SpaceMaker logo, passcode field, **Unlock**, QR tip; states idle / wrong passcode / locked out (input and button disabled). After success the phone returns to the page it asked for.
- Same motion vocabulary as [ui-motion](../ui-motion/SPEC.md); no new animation.

## Acceptance criteria (BDD)

### Scenario: Default is open

- **Given** no passcode has ever been set
- **When** a non-loopback client requests `/gallery` and `/api/gallery/timeline`
- **Then** both succeed as today

### Scenario: Set a passcode

- **Given** Home is shown and no passcode is set
- **When** the user enters `hunter2` and presses **Set**
- **Then** the dock shows the Active state with a masked field
- **And** a non-loopback request without a login to `/api/gallery/timeline` returns 401 `passcode-required`

### Scenario: Passcode too short

- **Given** Home is shown
- **When** the user enters `abc` and presses **Set**
- **Then** an inline error is shown and no passcode is stored

### Scenario: Desktop is never asked

- **Given** a passcode is set
- **When** a loopback client requests any page or API
- **Then** it is served without a login

### Scenario: Phone unlocks with the passcode

- **Given** a passcode is set and a phone has no login
- **When** it opens `/gallery`
- **Then** it receives the unlock page
- **When** it submits the correct passcode
- **Then** the login cookie is set and `/gallery` loads

### Scenario: QR signs a phone in

- **Given** a passcode is set
- **When** the phone opens a QR URL ending in `#k=<token>`
- **Then** the unlock page exchanges the token and loads the requested page without prompting

### Scenario: Wrong passcode

- **Given** a passcode is set
- **When** a phone submits a wrong passcode
- **Then** the response is 401 and the page shows "Wrong passcode. Try again."

### Scenario: Lockout after repeated failures

- **Given** a phone has submitted 5 consecutive wrong passcodes
- **When** it submits any passcode within 30 s
- **Then** the response is 429 with the seconds remaining and the passcode is not evaluated
- **And** the next lockout from that IP lasts 60 s

### Scenario: Change or clear signs everyone out

- **Given** a phone is logged in
- **When** the user changes or clears the passcode on the desktop
- **Then** the phone's next API request returns 401 (or, if cleared, is served openly)
- **And** an old QR token no longer works

### Scenario: Remembered across restarts

- **Given** a passcode is set and the app is restarted
- **When** the app starts
- **Then** the dock shows the Active state and previously logged-in phones remain logged in

### Scenario: Corrupt stored passcode

- **Given** the stored hash is unreadable
- **When** the app starts
- **Then** the passcode is cleared, Home shows a warning, and requests are served as with no passcode

### Scenario: Desktop-only routes unaffected

- **Given** a passcode is set and a phone is logged in
- **When** the phone calls a loopback-only route such as `PUT /api/settings`
- **Then** the response is 403 `desktop-only`

### Scenario: Token never reaches server logs

- **Given** a QR URL contains `#k=<token>`
- **When** the phone loads it
- **Then** no request line or query string sent to the server contains the token until `POST /api/unlock`

### Scenario: Plaintext never stored

- **Given** a passcode is set
- **When** the settings file is read
- **Then** it contains a salted scrypt hash and a token secret but not the passcode

## Out of scope

- Encrypting library files, thumbnails, the index, or HTTP traffic (AES/TLS/HTTPS certificates) — a separate future feature.
- Per-user accounts, multiple passcodes, expiry or revoking a single device.
- Protecting against a network sniffer or a compromised desktop account.
- Passcode recovery (clear it from the desktop).
