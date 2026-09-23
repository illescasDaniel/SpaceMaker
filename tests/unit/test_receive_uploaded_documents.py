from pathlib import Path

from spacemaker.application.receive_uploaded_documents import ReceiveUploadedDocuments


class FakeFs:
	def __init__(self, tmp_path: Path) -> None:
		self._root = tmp_path

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


def test_given_valid_relative_path_when_ingest_then_saved_under_dest_root(tmp_path):
	fs = FakeFs(tmp_path)
	use_case = ReceiveUploadedDocuments(fs)
	temp = tmp_path / "temp.bin"
	temp.write_bytes(b"hello")
	dest_root = str(tmp_path / "docs")

	outcome = use_case.ingest(dest_root, "folder/note.txt", temp_path=str(temp), incoming_size=5)

	assert outcome.disposition.value == "saved"
	assert (tmp_path / "docs" / "folder" / "note.txt").read_bytes() == b"hello"
