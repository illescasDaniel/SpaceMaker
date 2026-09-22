# SpaceMaker

Local backup, convert (AVIF/AV1), and gallery for Android media. Spec-driven, hexagonal Python app.

## Development

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv run task sync-dev
uv run task dev-tools -- --from-path   # populate tools/ (magick, ffmpeg, adb, …)
uv run task checks
uv run task checks -- --fix
uv run task spacemaker                 # desktop app
```

SpaceMaker runs **bundled CLIs from `tools/`**, not your system `PATH`. See [tools/README.md](tools/README.md) and [specs/packaging/SPEC.md](specs/packaging/SPEC.md).

Web lint/format (Biome, ESLint-class checks for JS in wireframes and static UI):

```bash
npm ci
npm run check
```

See [AGENTS.md](AGENTS.md), [specs/](specs/), and [docs/legal/](docs/legal/) (privacy, bundled tools, disclaimer).
