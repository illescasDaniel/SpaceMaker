# LAN access policy (what other devices can reach)

## Metadata

- **Feature:** Only the computer running SpaceMaker (and its own browser) can use the app GUI and control APIs; other devices on the network reach only the gallery and the QR upload/download pages.
- **Wireframe:** [wireframes/phone-desktop-only.html](../../wireframes/phone-desktop-only.html) — **approved** 2026-10-19 (chat)
- **Spec approved:** 2026-10-19 (chat), incl. gallery writes LAN-allowed and the Open gallery notice page; architecture approved 2026-10-19
- **User direction (2026-10-19):** "the program GUI should only be accessible from the computer running the app/server and its browser. other devices on the local network should only access the gallery and download/upload endpoints."
- **Related:** [network-passcode](../network-passcode/SPEC.md), [gallery](../gallery/SPEC.md), [receive-files](../receive-files/SPEC.md), [send-files](../send-files/SPEC.md), [transfer-files](../transfer-files/SPEC.md), [device-file-picker](../device-file-picker/SPEC.md)

## Design decisions

| Decision | Choice |
|---|---|
| **Success criteria** | A request from a non-loopback client can never load the desktop app shell or call a control/state API; it can still use the gallery and the QR upload/download pages exactly as today. Loopback behaviour is unchanged. |
| **Failure handling** | Desktop-only API called from the LAN → `403 {"detail": "desktop-only"}` (same as today’s `require_loopback`). `GET /` from the LAN → the notice page (HTTP 200) with an **Open gallery** link. With a passcode set and no login the passcode gate still answers first (401 / unlock page). |
| **Performance & resource budget** | One IP check per request, no I/O, no new dependencies. |
| **Trust boundary** | The decision uses the **TCP peer address** (`request.client.host`), never the `Host` header. Today `/` picks the desktop shell from the `Host` header, so a LAN client sending `Host: localhost` gets the desktop shell; this spec removes that. A reverse proxy on the same machine would appear as loopback — out of scope (document only). |

## Rules

1. **LAN-allowed** (reachable by non-loopback clients, subject to the network passcode and existing QR tokens): gallery pages and APIs, `/thumbs`, `/media`, the five phone pages and their session/upload/download endpoints, `POST /api/unlock`, `/favicon.ico`, `/static/*`.
2. **Desktop-only**: everything else — the main app shell (`/` for the desktop), control and state APIs, QR image endpoints, settings, tools, devices, the USB/extract/convert jobs, passcode management, `/api/server-info`, `/api/legal/*`, devtools stubs, and `/ws`.
3. `GET /` from a non-loopback client returns the notice page, not the app. `/gallery` and `/gallery/item/*` keep returning the mobile gallery shell to non-loopback clients and the desktop shell (gallery screen) to loopback.
4. **`--server-only` mode:** the server still binds to the LAN so the gallery and QR pages work for phones, but its GUI now works only from a browser **on the same machine** (for example `http://localhost:PORT`). A phone or another computer opening the address sees the notice page. Users who relied on controlling a headless server from another device lose that; they must use the gallery/QR pages instead.
5. Adding a new route requires choosing a policy; the route-audit test below fails if a route is neither on the LAN allow-list nor guarded.

## Route table (every route in `adapters/inbound/web`)

| Method | Route | Policy | Notes | Today |
|---|---|---|---|---|
| GET | `/` | **Desktop** | LAN client gets the desktop-only notice page (wireframe), not the app shell | Host-header based; LAN gets `mobile_remote.html` |
| GET | `/gallery, /gallery/item/{path}` | **LAN** | Mobile gallery shell for LAN, desktop shell for loopback | — |
| GET | `/upload` | **LAN** | Photo backup QR page (token) | — |
| GET | `/upload/ended` | **LAN** | Ended page | — |
| GET | `/receive` | **LAN** | Receive files QR page (token) | — |
| GET | `/share` | **LAN** | Send files QR page (token) | — |
| GET | `/transfer` | **LAN** | Transfer files QR page (token) | — |
| GET | `/favicon.ico` | **LAN** | Needed by every page | — |
| GET | `/static/{file}` | **LAN** | Assets of the LAN pages. `index.html` is also reachable here but is inert without desktop APIs (all desktop-only) | — |
| GET | `/json/version, /json/list` | **Desktop** | Chromium devtools stubs for the desktop webview | Open today |
| GET | `/thumbs/{path}, /media/{path}` | **LAN** | Gallery media (thumbnails, originals/processed streaming) | — |
| GET | `/api/gallery/timeline` | **LAN** | Gallery browse | — |
| GET | `/api/gallery/calendar` | **LAN** | Gallery browse | — |
| GET | `/api/gallery/item` | **LAN** | Gallery browse | — |
| GET | `/api/gallery/day` | **LAN** | Gallery browse | — |
| GET | `/api/gallery/item/neighbor` | **LAN** | Gallery browse | — |
| DELETE | `/api/gallery/item` | **LAN** | Gallery (delete/trash/convert/export stay as in the gallery spec) | — |
| POST | `/api/gallery/export` | **LAN** | Gallery (delete/trash/convert/export stay as in the gallery spec) | — |
| GET | `/api/gallery/export/{job_id}` | **LAN** | Gallery (delete/trash/convert/export stay as in the gallery spec) | — |
| GET | `/api/gallery/export/{job_id}/file` | **LAN** | Gallery (delete/trash/convert/export stay as in the gallery spec) | — |
| POST | `/api/gallery/batch/trash` | **LAN** | Gallery (delete/trash/convert/export stay as in the gallery spec) | — |
| POST | `/api/gallery/batch/convert` | **LAN** | Gallery (delete/trash/convert/export stay as in the gallery spec) | — |
| GET | `/api/gallery/batch/convert/{job_id}` | **LAN** | Gallery (delete/trash/convert/export stay as in the gallery spec) | — |
| GET | `/api/gallery/batch/convert/{job_id}/file` | **LAN** | Gallery (delete/trash/convert/export stay as in the gallery spec) | — |
| POST | `/api/gallery/batch/download` | **LAN** | Gallery (delete/trash/convert/export stay as in the gallery spec) | — |
| POST | `/api/gallery/open` | **Desktop** | Opens a file in the OS viewer / maps on the computer | Loopback-only |
| GET | `/api/upload/session` | **LAN** | Photo backup phone session | — |
| POST | `/api/upload` | **LAN** | Photo backup upload | — |
| GET | `/api/receive/session` | **LAN** | Phone page session (token-gated) | — |
| POST | `/api/receive` | **LAN** | Receive files upload | — |
| GET | `/api/share/session` | **LAN** | Phone page session (token-gated) | — |
| GET | `/api/share/download` | **LAN** | Send files download | — |
| GET | `/api/transfer/session` | **LAN** | Phone page session (token-gated) | — |
| GET | `/api/transfer/download` | **LAN** | Phone page session (token-gated) | — |
| POST | `/api/transfer` | **LAN** | Transfer files upload | — |
| POST | `/api/unlock` | **LAN** | Passcode unlock (exempt from the passcode gate by design) | — |
| GET | `/api/network-passcode` | **Desktop** | Set/clear/read passcode | Loopback-only |
| PUT | `/api/network-passcode` | **Desktop** | Set/clear/read passcode | Loopback-only |
| DELETE | `/api/network-passcode` | **Desktop** | Set/clear/read passcode | Loopback-only |
| POST | `/api/convert/start` | **Desktop** |  | Loopback-only |
| POST | `/api/convert/stop` | **Desktop** |  | Loopback-only |
| POST | `/api/error/move-to-processed` | **Desktop** |  | Loopback-only |
| POST | `/api/device/list` | **Desktop** |  | Loopback-only |
| GET | `/api/device/thumb` | **Desktop** | Phone photo thumbnail | Loopback-only |
| GET | `/api/device/preview` | **Desktop** | Phone photo lightbox rendition | Loopback-only |
| GET | `/api/device/stream` | **Desktop** | Internal ranged phone-file reader for video posters (token-bound) | Loopback-only |
| PUT | `/api/device/view` | **Desktop** | Per-folder phone picker layout (List / Grid / Auto) | Loopback-only |
| GET | `/api/devices` | **Desktop** |  | Loopback-only |
| GET | `/api/library/counts` | **Desktop** |  | Loopback-only |
| POST | `/api/extract/start` | **Desktop** |  | Loopback-only |
| POST | `/api/extract/extras` | **Desktop** |  | Loopback-only |
| DELETE | `/api/extract/extras` | **Desktop** |  | Loopback-only |
| POST | `/api/extract/pause` | **Desktop** |  | Loopback-only |
| POST | `/api/extract/resume` | **Desktop** |  | Loopback-only |
| POST | `/api/extract/stop` | **Desktop** |  | Loopback-only |
| GET | `/api/extract/upload-qr.svg` | **Desktop** |  | Loopback-only |
| POST | `/api/share/selection` | **Desktop** |  | Loopback-only |
| POST | `/api/transfer/add` | **Desktop** |  | Loopback-only |
| POST | `/api/transfer/save` | **Desktop** |  | Loopback-only |
| GET | `/api/receive/qr.svg` | **Desktop** |  | Loopback-only |
| GET | `/api/share/qr.svg` | **Desktop** |  | Loopback-only |
| GET | `/api/transfer/qr.svg` | **Desktop** |  | Loopback-only |
| GET | `/api/defaults` | **Desktop** |  | Loopback-only |
| GET | `/api/settings` | **Desktop** |  | Loopback-only |
| PUT | `/api/settings` | **Desktop** |  | Loopback-only |
| POST | `/api/preferences/clear` | **Desktop** |  | Loopback-only |
| POST | `/api/browser-cache/clear` | **Desktop** |  | Loopback-only |
| POST | `/api/library/reset` | **Desktop** |  | Loopback-only |
| POST | `/api/easy/bootstrap` | **Desktop** |  | Loopback-only |
| POST | `/api/module/enter` | **Desktop** |  | Loopback-only |
| POST | `/api/module/home` | **Desktop** |  | Loopback-only |
| POST | `/api/documents/open-folder` | **Desktop** |  | Loopback-only |
| POST | `/api/library/open-folder` | **Desktop** |  | Loopback-only |
| POST | `/api/usb-transfer/open-folder` | **Desktop** |  | Loopback-only |
| GET | `/api/tools/status` | **Desktop** |  | Loopback-only |
| POST | `/api/tools/ensure` | **Desktop** |  | Loopback-only |
| POST | `/api/tools/components-continue` | **Desktop** |  | Loopback-only |
| DELETE | `/api/tools/downloaded` | **Desktop** |  | Loopback-only |
| POST | `/api/usb-transfer/start` | **Desktop** |  | Loopback-only |
| POST | `/api/usb-transfer/extras` | **Desktop** |  | Loopback-only |
| DELETE | `/api/usb-transfer/extras` | **Desktop** |  | Loopback-only |
| POST | `/api/usb-transfer/pause` | **Desktop** |  | Loopback-only |
| POST | `/api/usb-transfer/resume` | **Desktop** |  | Loopback-only |
| POST | `/api/usb-transfer/stop` | **Desktop** |  | Loopback-only |
| WS | `/ws` | **Desktop** | Live app state | Loopback-only |
| GET | `/api/server-info` | **Desktop** | Reveals the gallery URL **with login token** and firewall status | **Open to LAN today** — gap |
| GET | `/api/gallery/qr.svg` | **Desktop** | QR of the gallery URL with login token | **Open to LAN today** — gap |
| GET | `/api/legal/{doc_id}` | **Desktop** | Legal text shown in the desktop UI | **Open to LAN today** — gap |

**Net change from today** (rows marked *gap*/Host-header): `GET /` (client-IP instead of Host header, new notice copy), `GET /json/version`, `GET /json/list`, `GET /api/server-info`, `GET /api/gallery/qr.svg`, `GET /api/legal/{doc_id}` become desktop-only. Everything else already matches. Implementation note: `gallery-timeline.js` calls `/api/server-info` and `/api/gallery/qr.svg` for the desktop gallery share panel; it must skip them on the mobile gallery shell.

## Open questions for approval

- Gallery write actions (delete item, batch trash/convert, export) are LAN-allowed today and stay so here ("gallery endpoints"). Make them desktop-only instead?
- Notice page: link to **Open gallery** (wireframe) vs plain redirect to `/gallery`.

## Behaviour (BDD)

### Scenario: LAN client opens the app address

- **Given** a non-loopback client (any `Host` header, including `localhost`)
- **When** it requests `GET /`
- **Then** it receives the desktop-only notice page with an **Open gallery** link, never `index.html`

### Scenario: LAN client calls a control API

- **Given** a non-loopback client with a valid login (or no passcode set)
- **When** it calls any desktop-only route in the table (for example `PUT /api/settings`, `POST /api/module/enter`, `GET /api/server-info`)
- **Then** the response is 403 `desktop-only`

### Scenario: LAN client websocket

- **Given** a non-loopback client
- **When** it opens `/ws`
- **Then** the connection is refused

### Scenario: LAN client uses the gallery and QR pages

- **Given** a non-loopback client (logged in if a passcode is set)
- **When** it opens `/gallery`, browses media, or uses `/upload`, `/receive`, `/share`, `/transfer` with a valid QR token
- **Then** everything works as today

### Scenario: Desktop is unaffected

- **Given** a loopback client (desktop app or a browser on the same machine, including `--server-only`)
- **When** it requests `/` or any route in the table
- **Then** it gets the full app and all APIs, with no passcode prompt

### Scenario: Route audit

- **Given** every route registered on the FastAPI app
- **When** the audit test lists them
- **Then** each is either on the LAN allow-list of this spec or answers 403 `desktop-only` to a non-loopback client

## Out of scope

- Authentication changes (passcode behaviour is unchanged), TLS, per-device permissions.
- Making gallery write actions desktop-only (open question above).
- Proxy / tunnel setups where the peer address is loopback.
