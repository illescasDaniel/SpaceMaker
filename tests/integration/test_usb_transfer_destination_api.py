from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from spacemaker.bootstrap.services import create_app
from spacemaker.domain.jobs import JobPhase


pytestmark = pytest.mark.integration


def _put(client: TestClient, destination: str | None, library_root: str) -> int:
	body: dict[str, object] = {"library_root": library_root, "connection_method": "adb"}
	if destination is not None:
		body["usb_transfer_destination"] = destination
	return client.put("/api/settings", json=body).status_code


def test_given_default_when_snapshot_then_destination_is_documents_spacemaker(tmp_path) -> None:
	# given
	client = TestClient(create_app())
	# when
	snap = client.get("/api/settings").json()
	# then
	assert snap["usb_transfer_destination"].endswith("SpaceMaker")
	assert snap["usb_transfer_destination_custom"] is False


def test_given_absolute_destination_when_put_then_snapshot_and_restart_keep_it(tmp_path) -> None:
	# given
	target = str(tmp_path / "Phone files")
	client = TestClient(create_app())
	# when
	status = _put(client, target, str(tmp_path / "lib"))
	# then
	assert status == 200
	snap = client.get("/api/settings").json()
	assert snap["usb_transfer_destination"] == target
	assert snap["usb_transfer_destination_custom"] is True
	restarted = TestClient(create_app()).get("/api/settings").json()
	assert restarted["usb_transfer_destination"] == target


def test_given_custom_destination_when_put_empty_then_default_restored(tmp_path) -> None:
	# given
	client = TestClient(create_app())
	_put(client, str(tmp_path / "x"), str(tmp_path / "lib"))
	# when
	_put(client, "", str(tmp_path / "lib"))
	# then
	snap = client.get("/api/settings").json()
	assert snap["usb_transfer_destination_custom"] is False


def test_given_relative_destination_when_put_then_400_and_nothing_stored(tmp_path) -> None:
	# given
	client = TestClient(create_app())
	# when
	status = _put(client, "Backups/phone", str(tmp_path / "lib"))
	# then
	assert status == 400
	assert client.get("/api/settings").json()["usb_transfer_destination_custom"] is False


def test_given_settings_without_destination_field_when_put_then_choice_unchanged(tmp_path) -> None:
	# given
	target = str(tmp_path / "keep")
	client = TestClient(create_app())
	_put(client, target, str(tmp_path / "lib"))
	# when
	_put(client, None, str(tmp_path / "lib"))
	# then
	assert client.get("/api/settings").json()["usb_transfer_destination"] == target


def test_given_running_transfer_when_put_destination_then_ignored(tmp_path) -> None:
	# given
	app = create_app()
	client = TestClient(app)
	app.state.services.session.usb_transfer_phase = JobPhase.RUNNING
	# when
	_put(client, str(tmp_path / "late"), str(tmp_path / "lib"))
	# then
	assert client.get("/api/settings").json()["usb_transfer_destination_custom"] is False
