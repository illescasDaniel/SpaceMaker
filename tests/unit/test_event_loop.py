from spacemaker.bootstrap import event_loop


def test_given_win32_when_resolve_loop_then_points_at_selector_event_loop_class(monkeypatch):
	monkeypatch.setattr(event_loop.sys, "platform", "win32")

	assert event_loop.uvicorn_loop_for_platform() == "asyncio:SelectorEventLoop"


def test_given_non_win32_when_resolve_loop_then_uses_uvicorn_default(monkeypatch):
	monkeypatch.setattr(event_loop.sys, "platform", "linux")

	assert event_loop.uvicorn_loop_for_platform() == "auto"
