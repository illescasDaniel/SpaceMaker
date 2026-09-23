# SpaceMaker

Local backup, convert (AVIF/AV1), and gallery for Android media. Spec-driven, hexagonal Python app.

## Development

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv run task sync-dev
uv run task checks
uv run task checks -- --fix
uv run task spacemaker                 # desktop app
```

On first launch the app downloads pinned CLIs into your user data folder. **Settings** shows each component’s status. System `PATH` is used only after you choose **Continue** on the setup screen (or with `SPACEMAKER_DEV=1`). See [tools/README.md](tools/README.md) and [specs/packaging/SPEC.md](specs/packaging/SPEC.md).

Web lint/format (Biome, ESLint-class checks for JS in wireframes and static UI):

```bash
npm ci
npm run check
```

See [AGENTS.md](AGENTS.md), [specs/](specs/), and [docs/legal/](docs/legal/) (privacy, third-party tools, disclaimer).
