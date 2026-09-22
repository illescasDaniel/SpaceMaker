# Fast tests (srxy-inspired)

## Layout

| Directory | Purpose |
|-----------|---------|
| `tests/unit/` | Domain, application, adapter logic with mocks |
| `tests/integration/` | Adapters with faked subprocess (future) |
| `tests/conftest.py` | Shared fixtures, markers |

## Naming

```python
def test_given_valid_avif_when_convert_then_moves_to_converted_without_reencode():
	# given
	...
	# when
	...
	# then
	...
```

## Speed rules

- Unit tests: no real `ffmpeg`, `magick`, or `adb`. Use fakes in `tests/unit/fakes.py`.
- Use `tmp_path` when testing real filesystem adapters later.
- Mark slow integration tests `@pytest.mark.integration`.

## Quality gate

```bash
uv run task sync-dev
uv run task checks
uv run task checks -- --fix
npm ci && npm run check   # Biome for wireframes / static JS
```

Python: **ruff** (lint+format, tabs), **ty** (types), **pytest** via `scripts/quality/checks.sh`.

Integration tests that hit FastAPI should use **`httpx2`** with Starlette’s async client (or equivalent) instead of `TestClient` + legacy **`httpx`**, so pytest stays warning-clean (Starlette deprecates the old pairing).

Web: **Biome** (lint + format, ESLint-class rules) via `package.json`.
