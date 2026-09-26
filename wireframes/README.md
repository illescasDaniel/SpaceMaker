# Wireframes

Self-contained HTML mocks for UX review **before** writing `specs/` or application code.

| File | Purpose |
|------|---------|
| [app.html](app.html) | Desktop app: Home hub, Photo/USB photo/USB file/Receive/Send modules, Advanced wizard, Gallery |
| [phone-upload.html](phone-upload.html) | Phone web page: photo/video upload (Photo backup QR) |
| [phone-receive.html](phone-receive.html) | Phone web page: any file upload (Receive files QR) |
| [phone-share.html](phone-share.html) | Phone web page: download list (Send files QR) |

Open in any browser:

```bash
xdg-open wireframes/app.html
xdg-open wireframes/phone-upload.html
xdg-open wireframes/phone-receive.html
xdg-open wireframes/phone-share.html
```

Production UI lives under `src/spacemaker/adapters/inbound/web/static/` and should match approved wireframes:

| Wireframe | Production |
|-----------|------------|
| `phone-upload.html` | `static/upload.html` |
| `phone-receive.html` | `static/receive.html` |
| `phone-share.html` | `static/share.html` |
| `app.html` (Gallery tab, narrow viewport) | `static/gallery_mobile.html` + `static/index.html` |
