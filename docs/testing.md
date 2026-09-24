# Testing Standards

Full playbook: [docs/playbooks/fast-tests.md](playbooks/fast-tests.md) and
the `.cursor/skills/fast-tests/` skill. This page is the browsable summary;
the playbook is the source of truth if they ever disagree.

## Layout

| Directory | Purpose |
|-----------|---------|
| `tests/unit/` | Domain, application, adapter logic — fast, no real subprocess/network I/O |
| `tests/integration/` | Adapters exercised more end-to-end (e.g. the FastAPI app itself) |
| `tests/conftest.py` | Shared fixtures, markers |
| `tests/unit/fakes.py` | In-memory fakes for outbound ports (`FakeFileSystem`, `FakeMediaConverter`, `FakeMediaProbe`, ...) |

Run everything: `uv run pytest` (or `uv run task checks` for the full quality
gate — ruff + ty + pytest).

## BDD naming: given / when / then

Every test name follows `test_given_<state>_when_<action>_then_<outcome>`,
with matching `# given` / `# when` / `# then` comment sections in the body.
Real example, from [tests/unit/test_convert_media.py](../tests/unit/test_convert_media.py):

```python
def test_given_avif_in_originals_when_convert_then_moves_to_converted():
	# given
	fs = FakeFileSystem()
	library = "/lib"
	rel = "x.avif"
	fs.files[_paths(fs, library, LibraryFolder.ORIGINALS, rel)] = 10
	probe = FakeMediaProbe()
	converter = FakeMediaConverter()
	converter.bind_filesystem(fs)
	use_case = ConvertMedia(fs, converter, probe)
	# when
	use_case.run(library)
	# then
	assert _paths(fs, library, LibraryFolder.ORIGINALS, rel) not in fs.files
	assert fs.files[_paths(fs, library, LibraryFolder.CONVERTED, rel)] == 10
```

This keeps each test readable as a single scenario and makes the failure
message ("...when_convert_then_moves_to_converted" failed) tell you what
behavior broke without opening the file.

## Mocking standards

- **Unit tests never shell out.** No real `ffmpeg`, `magick`, `adb`, or
  filesystem I/O beyond `tmp_path` when a test genuinely needs a real path.
  Outbound ports (`FileSystem`, `MediaConverter`, `MediaProbe`,
  `DeviceRepository`, ...) get **hand-written in-memory fakes** in
  `tests/unit/fakes.py`, injected into the use case under test — not
  `unittest.mock.Mock`/`MagicMock` stand-ins for ports. A fake models real
  behavior (e.g. `FakeFileSystem` tracks a `dict[str, int]` of paths → sizes
  and actually moves/copies/deletes entries), so a wrong call sequence fails
  the test instead of silently returning a `Mock`.
- Use cases are tested by constructing them directly with fakes
  (`ConvertMedia(fs, converter, probe)`), not through the web layer —
  keeps unit tests fast and decoupled from FastAPI.
- Platform-conditional tests use a local `_skip_on_windows` marker
  (`pytest.mark.skipif(sys.platform == "win32", reason="...")`) for logic
  that genuinely only applies on POSIX (e.g. shell-script-based RAW
  conversion) — see `tests/unit/test_raw_image_convert.py`,
  `test_raw_preview.py`, `test_tool_runner.py`. Don't skip a test just
  because it's inconvenient on one OS; only for a real platform constraint.

## Integration tests

`tests/integration/` exercises real adapters together — currently the
FastAPI app via `fastapi.testclient.TestClient` against `bootstrap.services.create_app()`
(see `tests/integration/test_web_app.py`, `test_loopback_api.py`), marked
module-wide with `pytestmark = pytest.mark.integration`.

**Known direction, not yet done:** the playbook calls for migrating off
`TestClient` + legacy `httpx` to **`httpx2`** with Starlette's async client,
since Starlette is deprecating that pairing and it currently emits
deprecation warnings. New integration tests should prefer `httpx2` where
practical; don't block on migrating existing ones as a prerequisite for
unrelated work.

## Speed rules

- Keep `tests/unit/` fast enough to run on every save — no real subprocess,
  no real network, no sleeping.
- `pytest-xdist` is installed for parallel runs; `scripts/quality/pytest.sh`
  runs `tests/unit tests/integration` together via `uv run task checks`.
- No enforced coverage threshold currently (`pytest-cov` is installed but
  not gated in CI/`checks.sh`) — don't assume one exists; write tests for
  behavior, not for a percentage.

## Quality gate

```bash
uv run task sync-dev
uv run task checks
uv run task checks -- --fix
npm ci && npm run check   # Biome for wireframes / static JS
```

Python: **ruff** (lint + format, tabs), **ty** (types), **pytest**. Web:
**Biome**.
