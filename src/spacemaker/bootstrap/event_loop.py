from __future__ import annotations

import sys


def uvicorn_loop_for_platform() -> str:
	"""Windows: point uvicorn's `loop=` at asyncio.SelectorEventLoop instead of its
	default ("auto"), which resolves to ProactorEventLoop on Windows.

	ProactorEventLoop logs a noisy (but harmless) ConnectionResetError from
	_ProactorBasePipeTransport._call_connection_lost whenever a client resets the TCP
	connection mid-request (e.g. a phone losing Wi-Fi while polling /api/upload/session)
	-- a long-standing asyncio stdlib bug: https://github.com/python/cpython/issues/149388
	(bpo-38856). SelectorEventLoop doesn't have this bug; this app only ever uses blocking
	subprocess.run/Popen (never asyncio subprocess/pipes), so it doesn't need anything
	Proactor-only provides.

	`asyncio.set_event_loop_policy()` would be the more obvious fix but is deprecated as
	of Python 3.14 (removal in 3.16) -- using uvicorn's own `loop=` customization point
	avoids it entirely.

	Gotcha (don't reintroduce): a plain "module:attr" string pointing at a *function*
	does NOT go through the same `use_subprocess=...` factory-of-factories call that
	uvicorn's built-in named loops ("asyncio", "uvloop", ...) get --
	`uvicorn.config.Config.get_loop_factory()` only makes that extra call for names in
	its `LOOP_FACTORIES` table; for any other string it does
	`import_from_string(self.loop)` and uses the resolved object directly as the final
	zero-arg factory `asyncio.Runner` calls. Pointing that string at a wrapper function
	that *returns* `asyncio.SelectorEventLoop` (the class) left `asyncio.Runner._loop`
	holding the un-instantiated class itself -- every subsequent loop method call then
	failed with "missing 1 required positional argument: 'self'/'coro'", because it was
	using an unbound method. Pointing the string directly at the class fixes it: calling
	it via `SelectorEventLoop()` correctly instantiates the loop. Verified by
	tests/integration/test_server_smoke.py, which actually boots the real process (a
	regression here doesn't surface via FastAPI's in-process TestClient at all).
	"""
	if sys.platform != "win32":
		return "auto"
	return "asyncio:SelectorEventLoop"
