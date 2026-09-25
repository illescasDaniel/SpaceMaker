from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

from spacemaker.application.transfer_session import (
	EMPTY_TRANSFER_FOLDER_MESSAGE,
	EmptyTransferFolderError,
	StageTransferItem,
)
from spacemaker.domain.transfer_session import (
	TransferIngestDisposition,
	TransferItemKind,
	TransferOrigin,
	TransferSessionItem,
	allocate_transfer_display_name,
	folder_zip_display_name,
	next_suffixed_display_name,
)


class FakeFs:
	def exists(self, path: str) -> bool:
		return Path(path).is_file()

	def file_size(self, path: str) -> int:
		return Path(path).stat().st_size

	def ensure_parent_directory(self, file_path: str) -> None:
		Path(file_path).parent.mkdir(parents=True, exist_ok=True)

	def copy_file(self, source: str, destination: str) -> None:
		self.ensure_parent_directory(destination)
		Path(destination).write_bytes(Path(source).read_bytes())

	def delete_file(self, path: str) -> None:
		Path(path).unlink(missing_ok=True)


class FakeHasher:
	def sha256_file(self, path: str) -> str:
		return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _item(
	*,
	file_id: str = "i0",
	display_name: str = "report.pdf",
	content_hash: str = "abc",
	origin: TransferOrigin = TransferOrigin.PHONE,
) -> TransferSessionItem:
	return TransferSessionItem(
		file_id=file_id,
		display_name=display_name,
		staged_path=f"/tmp/{file_id}",
		content_hash=content_hash,
		kind=TransferItemKind.FILE,
		origin=origin,
	)


def test_given_free_name_when_allocate_display_name_then_uses_requested():
	# given
	existing: list[TransferSessionItem] = []

	# when
	allocation = allocate_transfer_display_name("notes.txt", "hash1", existing)

	# then
	assert allocation.disposition is TransferIngestDisposition.ADDED
	assert allocation.display_name == "notes.txt"


def test_given_same_name_and_same_hash_when_allocate_display_name_then_skips_duplicate():
	# given
	existing = [_item(display_name="report.pdf", content_hash="H")]

	# when
	allocation = allocate_transfer_display_name("report.pdf", "H", existing)

	# then
	assert allocation.disposition is TransferIngestDisposition.SKIPPED_DUPLICATE
	assert allocation.display_name == "report.pdf"


def test_given_same_name_and_different_hash_when_allocate_display_name_then_suffixes():
	# given
	existing = [_item(display_name="report.pdf", content_hash="H1")]

	# when
	allocation = allocate_transfer_display_name("report.pdf", "H2", existing)

	# then
	assert allocation.disposition is TransferIngestDisposition.ADDED
	assert allocation.display_name == "report (2).pdf"


def test_given_taken_suffixes_when_next_suffixed_display_name_then_picks_next_free():
	# given
	taken = {"report.pdf", "report (2).pdf"}

	# when
	name = next_suffixed_display_name("report.pdf", taken)

	# then
	assert name == "report (3).pdf"


def test_given_folder_name_when_folder_zip_display_name_then_appends_zip():
	# given / when / then
	assert folder_zip_display_name("vacation") == "vacation.zip"
	assert folder_zip_display_name("vacation.zip") == "vacation.zip"


def test_given_empty_session_when_stage_file_then_added_under_staging(tmp_path):
	# given
	fs = FakeFs()
	hasher = FakeHasher()
	use_case = StageTransferItem(fs, hasher)
	staging = tmp_path / "staging"
	temp = tmp_path / "upload.bin"
	temp.write_bytes(b"hello")

	# when
	outcome = use_case.stage_file(
		str(staging),
		file_id="f1",
		requested_name="notes.txt",
		temp_path=str(temp),
		origin=TransferOrigin.PHONE,
		existing=[],
	)

	# then
	assert outcome.disposition is TransferIngestDisposition.ADDED
	assert outcome.item is not None
	assert outcome.item.display_name == "notes.txt"
	assert outcome.item.origin is TransferOrigin.PHONE
	assert (staging / "f1").read_bytes() == b"hello"
	assert not temp.exists()


def test_given_existing_same_hash_when_stage_file_then_skips_and_deletes_temp(tmp_path):
	# given
	fs = FakeFs()
	hasher = FakeHasher()
	use_case = StageTransferItem(fs, hasher)
	staging = tmp_path / "staging"
	staging.mkdir()
	existing_path = staging / "old"
	existing_path.write_bytes(b"same")
	digest = hashlib.sha256(b"same").hexdigest()
	existing = [
		TransferSessionItem(
			file_id="old",
			display_name="report.pdf",
			staged_path=str(existing_path),
			content_hash=digest,
			kind=TransferItemKind.FILE,
			origin=TransferOrigin.PC,
		),
	]
	temp = tmp_path / "dup.bin"
	temp.write_bytes(b"same")

	# when
	outcome = use_case.stage_file(
		str(staging),
		file_id="f2",
		requested_name="report.pdf",
		temp_path=str(temp),
		origin=TransferOrigin.PHONE,
		existing=existing,
	)

	# then
	assert outcome.disposition is TransferIngestDisposition.SKIPPED_DUPLICATE
	assert outcome.item is not None
	assert outcome.item.file_id == "old"
	assert not temp.exists()
	assert not (staging / "f2").exists()


def test_given_same_name_different_bytes_when_stage_file_then_stores_suffixed_name(tmp_path):
	# given
	fs = FakeFs()
	hasher = FakeHasher()
	use_case = StageTransferItem(fs, hasher)
	staging = tmp_path / "staging"
	staging.mkdir()
	existing_path = staging / "old"
	existing_path.write_bytes(b"first")
	existing = [
		TransferSessionItem(
			file_id="old",
			display_name="report.pdf",
			staged_path=str(existing_path),
			content_hash=hashlib.sha256(b"first").hexdigest(),
			kind=TransferItemKind.FILE,
			origin=TransferOrigin.PHONE,
		),
	]
	temp = tmp_path / "other.bin"
	temp.write_bytes(b"second")

	# when
	outcome = use_case.stage_file(
		str(staging),
		file_id="f2",
		requested_name="report.pdf",
		temp_path=str(temp),
		origin=TransferOrigin.PHONE,
		existing=existing,
	)

	# then
	assert outcome.disposition is TransferIngestDisposition.ADDED
	assert outcome.item is not None
	assert outcome.item.display_name == "report (2).pdf"
	assert (staging / "f2").read_bytes() == b"second"


def test_given_non_empty_folder_when_stage_folder_as_zip_then_one_zip_item(tmp_path):
	# given
	fs = FakeFs()
	hasher = FakeHasher()
	use_case = StageTransferItem(fs, hasher)
	folder = tmp_path / "vacation"
	folder.mkdir()
	(folder / "a.txt").write_text("a", encoding="utf-8")
	(folder / "sub").mkdir()
	(folder / "sub" / "b.txt").write_text("b", encoding="utf-8")
	staging = tmp_path / "staging"
	zip_temp = tmp_path / "tmp.zip"

	# when
	outcome = use_case.stage_folder_as_zip(
		str(staging),
		file_id="z1",
		folder_path=str(folder),
		origin=TransferOrigin.PC,
		existing=[],
		zip_temp_path=str(zip_temp),
	)

	# then
	assert outcome.disposition is TransferIngestDisposition.ADDED
	assert outcome.item is not None
	assert outcome.item.display_name == "vacation.zip"
	assert outcome.item.kind is TransferItemKind.FOLDER_ZIP
	assert outcome.item.origin is TransferOrigin.PC
	staged = Path(outcome.item.staged_path)
	assert staged.is_file()
	with zipfile.ZipFile(staged) as archive:
		assert set(archive.namelist()) == {"a.txt", "sub/b.txt"}
	assert not zip_temp.exists()


def test_given_empty_folder_when_stage_folder_as_zip_then_raises(tmp_path):
	# given
	fs = FakeFs()
	hasher = FakeHasher()
	use_case = StageTransferItem(fs, hasher)
	empty = tmp_path / "empty"
	empty.mkdir()

	# when / then
	try:
		use_case.stage_folder_as_zip(
			str(tmp_path / "staging"),
			file_id="z1",
			folder_path=str(empty),
			origin=TransferOrigin.PC,
			existing=[],
			zip_temp_path=str(tmp_path / "tmp.zip"),
		)
		raised = False
	except EmptyTransferFolderError as exc:
		raised = True
		assert str(exc) == EMPTY_TRANSFER_FOLDER_MESSAGE
	assert raised
