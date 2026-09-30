_Last updated: 2026-09-30 (MCP PyPI readiness pass; branch `claude/mcp-tools-pypi-review-727d33`)_

## Current focus

Getting `mcp-nav-shared`, `codenav-mcp` and `webnav-mcp` ready to publish to PyPI. Review and fixes are done (see `progress.md` 2026-09-30); `task checks` green (699).

Touched: `mcp-servers/*/pyproject.toml` + `README.md`, `codenav_mcp/ty_command.py` (+ new `tests/test_ty_command.py`), `mcp_nav_shared/lsp_client.py` (stderr tail), `webnav_mcp/web_index.py` (HTML attribute tokens), both `server.py` (`main()`, generic examples), `mcp_nav_shared/params.py`, `mcp_nav_shared/py.typed`, `docs/agent-tooling.md` (Publishing to PyPI).

## Next steps

1. Merge this branch; restart the MCP servers in the primary checkout.
2. Publish (user, needs a PyPI token): `uv build --package mcp-nav-shared`, then `codenav-mcp`, `webnav-mcp` into a scratch `dist/`; `uv publish` with the shared package first. Consider TestPyPI first.
3. After publishing, check `uvx codenav-mcp` / `uvx webnav-mcp` from PyPI in a non-uv project.

## Older open items

- Trial `code-grader` on the next real SDD feature.
- Exercise the `npm ci` fallback in `copy-venv.sh` next time a branch changes `package-lock.json`.
- Real-app check of the gallery delete animation on the user's library.
- Older open items in `progress.md` (ADB Browse slowness; Easy mode import; native pywebview hardware smoke).
