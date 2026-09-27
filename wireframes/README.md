# Wireframes

Self-contained HTML mocks for UX review **before** writing `specs/` or application code.

## Who is this text for?

Wireframes mix product UI with notes that must never ship. Use the right block:

| Block | Audience | Ships to production? |
|-------|----------|----------------------|
| Plain UI (buttons, titles, `.folder-hint`, etc.) | End user | **Yes** — implement in `static/` |
| `<p class="tip"><span class="tip-badge">Tip</span> …</p>` | End user (callout) | **Yes** — keep the Tip styling |
| `<aside class="wf-note" data-for="reviewer">` + **Review only** badge | You (design review) | **No** |
| `<aside class="wf-note" data-for="agent">` + **Agent note** badge | Coding agent | **No** |
| `<div class="wf-demo">` | Interactive wireframe controls | **No** |
| `.wireframe-banner` (top strip) | File chrome | **No** |

Striped dashed boxes = wireframe-only. If it isn’t labeled Tip / Review only / Agent note / Wireframe demo, treat it as product UI.

| File | Purpose |
|------|---------|
| [app.html](app.html) | Desktop app: Home hub, Photo/USB photo/USB file/Receive/Send/Transfer modules, Advanced wizard, Gallery |
| [phone-upload.html](phone-upload.html) | Phone web page: photo/video upload (Photo backup QR) |
| [phone-receive.html](phone-receive.html) | Phone web page: any file upload (Receive files QR) |
| [phone-share.html](phone-share.html) | Phone web page: download list (Send files QR) |
| [phone-transfer.html](phone-transfer.html) | Phone web page: shared temporary upload + download (Transfer files QR) |

Open in any browser:

```bash
xdg-open wireframes/app.html
xdg-open wireframes/phone-upload.html
xdg-open wireframes/phone-receive.html
xdg-open wireframes/phone-share.html
xdg-open wireframes/phone-transfer.html
```

Production UI lives under `src/spacemaker/adapters/inbound/web/static/` and should match approved wireframes:

| Wireframe | Production |
|-----------|------------|
| `phone-upload.html` | `static/upload.html` |
| `phone-receive.html` | `static/receive.html` |
| `phone-share.html` | `static/share.html` |
| `phone-transfer.html` | `static/transfer.html` (after spec approval) |
| `app.html` (Gallery tab, narrow viewport) | `static/gallery_mobile.html` + `static/index.html` |
