from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from spacemaker.bootstrap.services import AppServices
from spacemaker.domain.app_module import AppModule
from spacemaker.domain.download_all import DownloadAllBuildError, NothingToDownloadError
from spacemaker.domain.transfer_session import TransferOrigin


def _transfer_services(tmp_path: Path) -> AppServices:
	services = AppServices(port=8765, bind_host="127.0.0.1")
	services._documents_receive_root = str(tmp_path / "Documents" / "SpaceMaker")
	services.enter_module(AppModule.TRANSFER_FILES)
	return services


def _stage(services: AppServices, tmp_path: Path, name: str, data: bytes, origin=TransferOrigin.PHONE) -> None:
	temp = (
		tmp_path
		/ "incoming"
		/ f"{len(list((tmp_path / 'incoming').glob('*'))) if (tmp_path / 'incoming').exists() else 0}"
		/ name
	)
	temp.parent.mkdir(parents=True, exist_ok=True)
	temp.write_bytes(data)
	item = services.handle_transfer_upload_file(
		services._transfer_session_token, requested_name=name, temp_path=str(temp), origin=origin
	)
	assert item is not None


def _share_services(tmp_path: Path, *names: str) -> tuple[AppServices, str]:
	services = AppServices(port=8765, bind_host="127.0.0.1")
	paths = []
	for name in names:
		path = tmp_path / "shared" / name
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_bytes(name.encode())
		paths.append(str(path))
	services.set_share_selection(paths)
	return services, services._share_session_token


def test_given_transfer_items_from_pc_and_phone_when_transfer_download_all_then_zip_has_both(tmp_path) -> None:
	# given
	services = _transfer_services(tmp_path)
	_stage(services, tmp_path, "notes.txt", b"pc", TransferOrigin.PC)
	_stage(services, tmp_path, "report.pdf", b"phone", TransferOrigin.PHONE)
	# when
	zip_path = services.transfer_download_all(services._transfer_session_token)
	# then
	with zipfile.ZipFile(zip_path) as archive:
		assert sorted(archive.namelist()) == ["notes.txt", "report.pdf"]
	zip_path.unlink()
	services.shutdown()


def test_given_share_of_file_and_folder_when_share_download_all_then_zip_has_relative_paths(tmp_path) -> None:
	# given
	services = AppServices(port=8765, bind_host="127.0.0.1")
	report = tmp_path / "report.pdf"
	report.write_bytes(b"r")
	folder = tmp_path / "vacation"
	(folder / "day2").mkdir(parents=True)
	(folder / "a.jpg").write_bytes(b"a")
	(folder / "day2" / "b.jpg").write_bytes(b"b")
	services.set_share_selection([str(report), str(folder)])
	# when
	zip_path = services.share_download_all(services._share_session_token)
	# then
	with zipfile.ZipFile(zip_path) as archive:
		assert sorted(archive.namelist()) == ["report.pdf", "vacation/a.jpg", "vacation/day2/b.jpg"]
	zip_path.unlink()
	services.shutdown()


def test_given_wrong_token_when_transfer_download_all_then_permission_error_and_nothing_read(tmp_path) -> None:
	# given
	services = _transfer_services(tmp_path)
	_stage(services, tmp_path, "a.txt", b"a")
	# when
	# then
	with pytest.raises(PermissionError):
		services.transfer_download_all("wrong")
	services.shutdown()


def test_given_ended_session_when_transfer_download_all_then_permission_error(tmp_path) -> None:
	# given
	services = _transfer_services(tmp_path)
	token = services._transfer_session_token
	services.leave_module_for_home()
	# when
	# then
	with pytest.raises(PermissionError):
		services.transfer_download_all(token)
	services.shutdown()


def test_given_wrong_token_when_share_download_all_then_permission_error(tmp_path) -> None:
	# given
	services, _token = _share_services(tmp_path, "a.txt", "b.txt")
	# when
	# then
	with pytest.raises(PermissionError):
		services.share_download_all("wrong")
	services.shutdown()


def test_given_empty_transfer_session_when_transfer_download_all_then_nothing_to_download(tmp_path) -> None:
	# given
	services = _transfer_services(tmp_path)
	# when
	# then
	with pytest.raises(NothingToDownloadError):
		services.transfer_download_all(services._transfer_session_token)
	services.shutdown()


def test_given_share_file_vanished_when_share_download_all_then_other_files_zipped(tmp_path) -> None:
	# given
	services, token = _share_services(tmp_path, "a.txt", "b.txt", "c.txt")
	(tmp_path / "shared" / "b.txt").unlink()
	# when
	zip_path = services.share_download_all(token)
	# then
	with zipfile.ZipFile(zip_path) as archive:
		assert sorted(archive.namelist()) == ["a.txt", "c.txt"]
	zip_path.unlink()
	services.shutdown()


def test_given_all_share_files_vanished_when_share_download_all_then_nothing_to_download(tmp_path) -> None:
	# given
	services, token = _share_services(tmp_path, "a.txt", "b.txt")
	(tmp_path / "shared" / "a.txt").unlink()
	(tmp_path / "shared" / "b.txt").unlink()
	# when
	# then
	with pytest.raises(NothingToDownloadError):
		services.share_download_all(token)
	services.shutdown()


def test_given_build_failure_when_transfer_download_all_then_build_error_and_no_temp_zip_left(
	tmp_path, monkeypatch
) -> None:
	# given
	services = _transfer_services(tmp_path)
	_stage(services, tmp_path, "a.txt", b"a")
	temp_dir = tmp_path / "tmp"
	temp_dir.mkdir()
	monkeypatch.setattr("tempfile.tempdir", str(temp_dir))

	class _Failing:
		def build(self, kind, items, destination) -> None:
			Path(destination).write_bytes(b"partial")
			raise DownloadAllBuildError("disk full")

	services.download_all = _Failing()
	# when
	# then
	with pytest.raises(DownloadAllBuildError):
		services.transfer_download_all(services._transfer_session_token)
	assert list(temp_dir.iterdir()) == []
	assert len(services.transfer_manifest(services._transfer_session_token)) == 1
	services.shutdown()


def test_given_transfer_session_when_save_all_then_zip_saved_in_documents_and_tip_fields_returned(tmp_path) -> None:
	# given
	services = _transfer_services(tmp_path)
	for name in ("a.txt", "b.txt", "c.txt"):
		_stage(services, tmp_path, name, name.encode())
	# when
	saved = services.save_transfer_all_to_documents()
	# then
	assert saved["saved_name"] == "SpaceMaker-transfer.zip"
	assert Path(saved["saved_path"]).parent == tmp_path / "Documents" / "SpaceMaker"
	assert saved["saved_path_display"]
	with zipfile.ZipFile(saved["saved_path"]) as archive:
		assert sorted(archive.namelist()) == ["a.txt", "b.txt", "c.txt"]
	services.shutdown()


def test_given_existing_zip_in_documents_when_save_all_then_new_file_is_suffixed_and_first_untouched(tmp_path) -> None:
	# given
	services = _transfer_services(tmp_path)
	docs = tmp_path / "Documents" / "SpaceMaker"
	docs.mkdir(parents=True)
	(docs / "SpaceMaker-transfer.zip").write_bytes(b"old")
	_stage(services, tmp_path, "a.txt", b"a")
	# when
	saved = services.save_transfer_all_to_documents()
	# then
	assert saved["saved_name"] == "SpaceMaker-transfer (2).zip"
	assert (docs / "SpaceMaker-transfer.zip").read_bytes() == b"old"
	services.shutdown()


def test_given_ended_session_when_save_all_then_permission_error(tmp_path) -> None:
	# given
	services = _transfer_services(tmp_path)
	services.leave_module_for_home()
	# when
	# then
	with pytest.raises(PermissionError):
		services.save_transfer_all_to_documents()
	services.shutdown()


def test_given_empty_transfer_session_when_save_all_then_nothing_to_download(tmp_path) -> None:
	# given
	services = _transfer_services(tmp_path)
	# when
	# then
	with pytest.raises(NothingToDownloadError):
		services.save_transfer_all_to_documents()
	services.shutdown()
