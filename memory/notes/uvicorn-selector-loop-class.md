---
name: uvicorn-selector-loop-class
description: uvicorn loop= must name the loop class (asyncio:SelectorEventLoop), not a factory
type: decision
date: 2026-09-24
status: current
supersedes: uvicorn-selector-loop-factory
superseded_by:
source:
---

Fixed the SelectorEventLoop fix itself: uvicorn's custom `loop=` string must resolve to the loop class directly, not a factory function; added a real-process smoke test.

- **Context:** The previous entry's `event_loop.py` fix (`uvicorn.run(..., loop=uvicorn_loop_for_platform())` pointing a `"module:attr"` string at a `windows_selector_loop_factory()` function that returned `asyncio.SelectorEventLoop`) looked correct and passed all existing tests, but broke the app outright on the user's Windows machine — the server thread died instantly with `TypeError: BaseEventLoop.create_task() missing 1 required positional argument: 'coro'` and cascading "missing 1 required positional argument: 'self'" errors during shutdown. Reproduced locally with `uv run spacemaker --server-only` and bisected via `git stash`.
- **Root cause:** `uvicorn.config.Config.get_loop_factory()` only calls the resolved factory with `use_subprocess=...` for names in its `LOOP_FACTORIES` table (`"none"`/`"auto"`/`"asyncio"`/`"uvloop"`/`"zuvloop"`). For any other string (a custom `"module:attr"` path), it does `return import_from_string(self.loop)` and uses the resolved object **directly** as the final zero-arg factory `asyncio.Runner` calls — it does not call it a second time to unwrap a "factory of factories" the way the built-in `asyncio_loop_factory`/`uvloop_loop_factory` functions work. My function matched the shape of those built-ins (returning the *class*, expecting one more call) but was being used as a *custom* string, which skips that extra call — so `asyncio.Runner._loop` ended up holding the un-instantiated `SelectorEventLoop` class itself, and every subsequent method call on it (`create_task`, `shutdown_asyncgens`, `close`) failed as an unbound-method call.
- **Decision:** `uvicorn_loop_for_platform()` now returns the string `"asyncio:SelectorEventLoop"` directly (pointing straight at the stdlib class) instead of a wrapper function — no custom factory function needed at all. Verified via a standalone script that `uvicorn.Config(loop="asyncio:SelectorEventLoop").get_loop_factory()` resolves to the class and instantiates a working `_WindowsSelectorEventLoop`, then confirmed `uv run spacemaker --server-only` boots and serves a real request. Added `tests/integration/test_server_smoke.py` (new `smoke`-style integration test, and new `uv run task smoke` shortcut) that launches the actual `python -m spacemaker --server-only` process and polls a real endpoint — confirmed it reproduces this exact crash (full traceback dumped in the assertion message) when the previous broken function-based approach is reintroduced, and passes against the fix.
- **Rationale:** This bug was invisible to every existing test because they all use FastAPI's `TestClient` (in-process, no real `uvicorn.run()`/event-loop wiring at all) — only a test that boots the real OS process would catch it, which is exactly the gap the user asked to close ("create a proper smoke test... so that we run that smoke test the next time"). `tests/integration/test_server_smoke.py` runs as part of the normal `tests/integration` collection (`uv run task checks`), so it's not something that has to be remembered to run separately.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-24 — Fixed the SelectorEventLoop fix itself: uvicorn's custom `loop=` string must resolve to the loop class directly, not a factory function; added a real-process smoke test".
