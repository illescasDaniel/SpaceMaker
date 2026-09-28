from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from spacemaker.bootstrap.services import AppServices
from spacemaker.domain.compress_media import CompressMediaPreference
from spacemaker.domain.jobs import JobPhase
from spacemaker.domain.library import JobProgress, LibraryFolder
from spacemaker.domain.ui_mode import UiMode


def _easy_services(tmp_path: Path, monkeypatch) -> AppServices:
	services = AppServices(port=8765, bind_host="127.0.0.1")
	library = tmp_path / "lib"
	services.filesystem.ensure_library_folders(str(library))
	with services.session._lock:
		services.session.library_root = str(library)
		services.session.ui_mode = UiMode.EASY
	monkeypatch.setattr(
		services,
		"compress_media_preference",
		lambda: CompressMediaPreference(enabled=True, control_enabled=True, tools_available=True),
	)
	return services


def test_given_easy_idle_and_originals_when_maybe_start_convert_drain_then_starts(tmp_path: Path, monkeypatch):
	# given
	services = _easy_services(tmp_path, monkeypatch)
	library = services.session.library_root
	(Path(library) / LibraryFolder.ORIGINALS.value / "a.jpg").write_bytes(b"a")
	started: list[object] = []
	monkeypatch.setattr(services, "start_convert", lambda **kwargs: started.append(kwargs))
	# when
	services.maybe_start_convert_drain()
	# then
	assert len(started) == 1
	services.shutdown()


def test_given_convert_running_when_maybe_start_convert_drain_then_bumps_total_without_second_job(
	tmp_path: Path, monkeypatch
):
	# given
	services = _easy_services(tmp_path, monkeypatch)
	library = services.session.library_root
	originals = Path(library) / LibraryFolder.ORIGINALS.value
	(originals / "a.jpg").write_bytes(b"a")
	(originals / "b.jpg").write_bytes(b"b")
	with services.session._lock:
		services.session.convert_phase = JobPhase.RUNNING
		services.session.convert_progress = JobProgress(0, 1)
	started: list[object] = []
	monkeypatch.setattr(services, "start_convert", lambda **kwargs: started.append(kwargs))
	# when
	services.maybe_start_convert_drain()
	# then
	assert started == []
	assert services.session.convert_progress.completed == 0
	assert services.session.convert_progress.total == 2
	services.shutdown()


def test_given_wifi_upload_saved_when_handle_wifi_upload_then_calls_convert_drain(tmp_path: Path, monkeypatch):
	# given
	services = _easy_services(tmp_path, monkeypatch)
	services._extract_control = MagicMock()
	services._extract_control.accepts_new_file.return_value = True
	temp = tmp_path / "upload.jpg"
	temp.write_bytes(b"photo")
	drain_calls: list[int] = []
	monkeypatch.setattr(services, "maybe_start_convert_drain", lambda: drain_calls.append(1))
	monkeypatch.setattr(services, "wifi_token_valid", lambda _t: True)
	# when
	services.handle_wifi_upload("tok", "photo.jpg", str(temp), temp.stat().st_size)
	# then
	assert drain_calls == [1]
	services.shutdown()
