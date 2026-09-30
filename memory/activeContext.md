_Last updated: 2026-09-30 (MCP PyPI readiness merged into local `main`, not pushed)_

## Branch

`main` (primary checkout). Contains the Components UX work (`2d519d6`) and the merged `claude/mcp-tools-pypi-review-727d33` (MCP PyPI readiness pass). **Not pushed**: test first.

## Current focus

1. Test the merged MCP servers: restart them from this checkout (they run the primary's source), then exercise codenav/webnav, especially webnav `references`/`definition` on a name inside an HTML `id="…"`/`class="…"`, and a codenav tool error path.
2. Components smoke: restart the app → Components shows OK (not WARNING) when all tools resolve/system, Details collapsed, shorter lead; no ifuse/idevice on macOS.

## Just changed

- MCP packages (see `progress.md` / `decisions.md` 2026-09-30): codenav finds its bundled `ty`; language-server exit errors quote stderr; console scripts, LICENSE in wheels, PyPI metadata, rewritten READMEs, generic tool examples, `docs/agent-tooling.md` "Publishing to PyPI".
- Components UX polish work from `2d519d6` (see `progress.md`).

## Next steps

1. After testing, push `main`.
2. Publish (needs your PyPI token): `uv build --package mcp-nav-shared`, then `codenav-mcp`, `webnav-mcp` into a scratch `dist/`; `uv publish` the shared package first. Consider TestPyPI first. Then check `uvx codenav-mcp` / `uvx webnav-mcp` in a non-uv project.

## Older open items

- Trial `code-grader` on the next real SDD feature.
- Exercise the `npm ci` fallback in `copy-venv.sh` next time a branch changes `package-lock.json`.
- Real-app check of the gallery delete animation on the user's library.
- Older open items in `progress.md` (ADB Browse slowness; Easy mode import; native pywebview hardware smoke).
