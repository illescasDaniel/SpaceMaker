from __future__ import annotations

from pathlib import Path

from spacemaker.bootstrap.services import AppServices
from spacemaker.domain.app_module import AppModule, LanSessionKind
from spacemaker.domain.transfer_session import TransferOrigin


def test_given_transfer_module_when_enter_then_session_active_with_qr_token():
	# given
	services = AppServices(port=8765, bind_host="127.0.0.1")

	# when
	services.enter_module(AppModule.TRANSFER_FILES)
	snap = services._transfer_files_snapshot()

	# then
	assert snap["active"] is True
	assert "/transfer?t=" in str(snap["page_url"])
	assert snap["item_count"] == 0
	assert services._lan_session_kind is LanSessionKind.TRANSFER_FILES

	services.shutdown()


def test_given_transfer_upload_when_home_then_staged_files_deleted(tmp_path):
	# given
	services = AppServices(port=8765, bind_host="127.0.0.1")
	services.enter_module(AppModule.TRANSFER_FILES)
	token = services._transfer_session_token
	temp = tmp_path / "notes.txt"
	temp.write_text("hello", encoding="utf-8")

	# when
	item = services.handle_transfer_upload_file(
		token,
		requested_name="notes.txt",
		temp_path=str(temp),
		origin=TransferOrigin.PHONE,
	)
	assert item is not None
	staged = Path(item.staged_path)
	assert staged.is_file()
	services.leave_module_for_home()

	# then
	assert not services.transfer_token_valid(token)
	assert not staged.exists()
	assert services._transfer_files_snapshot()["active"] is False

	services.shutdown()


def test_given_same_name_different_hash_when_two_uploads_then_suffix(tmp_path):
	# given
	services = AppServices(port=8765, bind_host="127.0.0.1")
	services.enter_module(AppModule.TRANSFER_FILES)
	token = services._transfer_session_token
	a = tmp_path / "a.pdf"
	b = tmp_path / "b.pdf"
	a.write_bytes(b"one")
	b.write_bytes(b"two")

	# when
	first = services.handle_transfer_upload_file(
		token,
		requested_name="report.pdf",
		temp_path=str(a),
		origin=TransferOrigin.PHONE,
	)
	second = services.handle_transfer_upload_file(
		token,
		requested_name="report.pdf",
		temp_path=str(b),
		origin=TransferOrigin.PC,
	)

	# then
	assert first is not None and first.display_name == "report.pdf"
	assert second is not None and second.display_name == "report (2).pdf"
	names = [row["name"] for row in services.transfer_manifest(token)]
	assert names == ["report.pdf", "report (2).pdf"]

	services.shutdown()
