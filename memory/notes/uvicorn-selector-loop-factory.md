---
name: uvicorn-selector-loop-factory
description: Windows Proactor ConnectionResetError noise: switch uvicorn to SelectorEventLoop via a factory
type: decision
date: 2026-09-24
status: superseded
supersedes:
superseded_by: uvicorn-selector-loop-class
source:
---

Windows ProactorEventLoop ConnectionResetError noise: switched uvicorn to SelectorEventLoop via `loop=` factory, not the deprecated asyncio policy API.

- **Context:** After confirming `--disable-gpu-compositing` fixed the WebEngine freeze (see the entry below), the user hit a different Windows-only traceback: `Exception in callback _ProactorBasePipeTransport._call_connection_lost()` / `ConnectionResetError: [WinError 10054]`, logged when a LAN client (phone) reset the TCP connection mid-request (e.g. polling `/api/upload/session`) — a long-standing, still-open CPython stdlib bug in `ProactorEventLoop` (https://github.com/python/cpython/issues/149388, bpo-38856), cosmetic (the request had already returned 200 OK), not a crash.
- **Decision:** New `src/spacemaker/bootstrap/event_loop.py`: `uvicorn_loop_for_platform()` returns uvicorn's default `"auto"` loop string everywhere except win32, where it returns a `"module:attr"` string pointing at `windows_selector_loop_factory()` (mirrors the shape of uvicorn's own `uvicorn.loops.asyncio.asyncio_loop_factory`, returns `asyncio.SelectorEventLoop`). Wired into `desktop.py`'s `run_server()` via `uvicorn.run(..., loop=uvicorn_loop_for_platform())`. Confirmed via a standalone script that `uvicorn.config.Config(loop=<that string>).get_loop_factory()` resolves to `asyncio.SelectorEventLoop` and instantiates `_WindowsSelectorEventLoop`. Verified no `asyncio` subprocess/pipe usage anywhere in `src/` (only blocking `subprocess.run`/`Popen`), so SelectorEventLoop's lack of Proactor-only capabilities doesn't matter here.
- **Rationale:** The obvious fix, `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())`, is deprecated as of Python 3.14 (removal in 3.16, confirmed via `ty check` warnings on this dev machine's 3.14.6 interpreter) — used uvicorn's own supported `loop=` customization point instead, which resolves via `uvicorn.importer.import_from_string` and is the documented way to hand uvicorn a non-default loop factory.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-24 — Windows ProactorEventLoop ConnectionResetError noise: switched uvicorn to SelectorEventLoop via `loop=` factory, not the deprecated asyncio policy API".

Superseded by [uvicorn-selector-loop-class](uvicorn-selector-loop-class.md).
