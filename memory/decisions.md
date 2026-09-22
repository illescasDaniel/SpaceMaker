# Technical decisions

Append-only log (newest first). Never rewrite history.

## 2026-09-22 — LAN firewall probe in bootstrap

- **Context:** Phone gallery failed when UFW blocked TCP 8765; users need in-app hints without guessing.
- **Decision:** `bootstrap/firewall.py` probes firewalld/UFW rules and a LAN TCP self-test; expose via `/api/server-info.firewall`. Shell helper `scripts/firewall/allow-spacemaker-port.sh` + task `firewall-allow`. Do not run MTP reconcile on every settings snapshot (blocks gallery clients).
- **Rationale:** Detection is best-effort but actionable; device scans stay on `/api/devices` only.

## 2026-09-22 — Gallery QR via segno (adapter-only)

- **Context:** Step 3 and LAN sharing need a scannable QR for `/gallery`; domain must stay free of QR libraries.
- **Decision:** Add `segno` as a runtime dependency; generate SVG at `GET /api/gallery/qr.svg` in the FastAPI adapter. Thumbnails lazy-generated under `{library}/.thumbnails/` via `SubprocessThumbnailGenerator` (ImageMagick / FFmpeg).
- **Rationale:** Keeps hexagonal boundaries; small dependency; EXIF dates via existing bundled ExifTool on `MediaProbePort.captured_at`.

## 2026-09-22 — Bundled CLIs + legal pack

- **Context:** User requires no manual third-party installs; privacy policy, third-party home pages, disclaimer in installer.
- **Decision:** All manifest tools bundled per OS/arch; `resolve_tool_path()` frozen vs dev. Docs in `docs/legal/`; spec `specs/legal/SPEC.md`; manifest YAML synced to `BundledTool` enum via tests.
- **Rationale:** Self-contained desktop product; transparency and liability coverage before public release.

## 2026-09-22 — Bundle adb per OS/arch

- **Context:** User wants ADB included in the final installer/binary, not a separate user install.
- **Decision:** Release builds ship Google platform-tools `adb` (and later libmtp) for each target OS/CPU; `AdbDeviceRepository` resolves bundled path first. PATH fallback only for dev/source runs. Spec: `specs/packaging/SPEC.md`.
- **Rationale:** Matches self-contained desktop app goal; adbutils still drives the client but must point at our binary.

## 2026-09-22 — Unified libmtp for MTP adapter

- **Context:** User asked whether Win/Linux users must install libmtp; OS already exposes MTP in Explorer/file managers.
- **Decision:** libmtp is the **application** MTP client on Windows, Linux, and macOS (one adapter path). User-facing copy: set phone to MTP only; do not tell Win/Linux users to install libmtp. Packaged app bundles libmtp tools when feasible.
- **Rationale:** Native OS MTP is for humans; SpaceMaker still needs libmtp (or equivalent) in code. Single stack beats WPD/gphoto2 split for v1.

## 2026-09-22 — MTP default, ADB recommended

- **Context:** User chose default extract path and platform tooling.
- **Decision:** Step 1 defaults to MTP; toggle to ADB (recommended) with info help. adbutils for ADB on all platforms.
- **Rationale:** Lower friction for casual users; ADB labeled recommended for speed/reliability when debugging is enabled.

## 2026-09-22 — uv quality gate and Biome for web

- **Context:** User requested srxy-style uv/ruff/ty checks plus JS lint for web UI.
- **Decision:** `pyproject.toml` + `uv run task checks` (`scripts/quality/checks.sh`: ruff, ty, pytest). Web: `package.json` + Biome 2.x on wireframes and future `static/` JS.
- **Rationale:** Matches Astral toolchain on Python; single fast linter/formatter for vanilla JS without separate ESLint+Prettier until needs grow.

## 2026-09-22 — Feature spec split

- **Context:** Step 2 SDD after wireframe approval.
- **Decision:** Four specs: `main-wizard`, `extract-media`, `convert-media`, `gallery` with cross-links; index at `specs/README.md`.
- **Rationale:** Matches hexagonal use cases and keeps convert policy testable in isolation.

## 2026-09-22 — SDD, wireframes, and test style

- **Context:** Greenfield SpaceMaker; user referenced GamesLibrary SDD and srxy tests.
- **Decision:** Markdown specs in `specs/<feature>/SPEC.md` (not Cucumber `.feature` files). Wireframes in `wireframes/` before specs. pytest with `test_given_…_when_…_then_…` naming and `# given` / `# when` / `# then` bodies (srxy style).
- **Rationale:** Matches existing agent workflows; keeps UX and behavior review separate; fast unit tests without Gherkin tooling.

## 2026-09-22 — Library folder layout and conversion outcomes

- **Context:** User refined conversion vs `convert_all_1_1.sh` with two-folder workflow extended to four outcomes.
- **Decision:** Library root contains `originals/`, `converted/`, `error/`, `invalid/`. Successful encode or move-as-is removes source from `originals/`. Failed encode: one retry, then `error/`. Unsupported/broken: `invalid/`. UI warnings with Review / Move-to-converted for errors.
- **Rationale:** Clear separation for gallery (`converted/` only), user review paths, and idempotent convert pipeline.

## 2026-09-22 — Compression reference

- **Context:** User's bash script encodes AVIF/AV1 rules, DNG+JPEG collision names, web-compat skip, size rollback.
- **Decision:** Vend `docs/reference/convert_all_1_1.sh` as authoritative compression reference; domain policy documented in `docs/playbooks/SpaceMaker-adaptations.md` and future specs.
- **Rationale:** Single repo-truth for FFmpeg/ImageMagick flags during spec and adapter implementation.
