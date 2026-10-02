from __future__ import annotations

import threading

import pytest
from starlette.testclient import TestClient

from spacemaker.bootstrap.services import create_app
from spacemaker.domain.jobs import JobPhase


pytestmark = pytest.mark.integration


def _put_settings_with_timeout(client: TestClient, *, body: dict[str, object], timeout: float = 5.0) -> int | None:
	result: dict[str, int] = {}

	def _call() -> None:
		result["status"] = client.put("/api/settings", json=body).status_code

	worker = threading.Thread(target=_call, daemon=True)
	worker.start()
	worker.join(timeout)
	return None if worker.is_alive() else result["status"]


@pytest.mark.parametrize("phase_attr", ["extract_phase", "usb_transfer_phase"])
def test_given_running_job_when_put_settings_then_responds_without_deadlock(
	phase_attr: str, tmp_path, monkeypatch
) -> None:
	# given
	monkeypatch.setenv("HOME", str(tmp_path))
	app = create_app()
	services = app.state.services
	setattr(services.session, phase_attr, JobPhase.RUNNING)
	client = TestClient(app)
	# when
	status = _put_settings_with_timeout(
		client,
		body={
			"library_root": str(tmp_path / "lib"),
			"connection_method": "wifi",
			"ui_mode": "easy",
		},
	)
	# then
	assert status == 200
