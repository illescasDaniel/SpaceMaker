from pathlib import Path

from tests.unit.fakes import FakeFileSystem

from spacemaker.application.receive_uploaded_media import ReceiveUploadedMedia, UploadDisposition
from spacemaker.domain.library import LibraryFolder


def test_given_existing_same_size_when_wifi_upload_then_skipped(tmp_path: Path):
	# given
	fs = FakeFileSystem()
	library = str(tmp_path / "lib")
	dest = fs.library_path(library, LibraryFolder.ORIGINALS, "DCIM/a.jpg")
	fs.files[dest] = 120
	source = tmp_path / "upload.bin"
	source.write_bytes(b"x" * 120)
	use_case = ReceiveUploadedMedia(fs)

	# when
	outcome = use_case.ingest(library, "DCIM/a.jpg", temp_path=str(source), incoming_size=120)

	# then
	assert outcome.disposition is UploadDisposition.SKIPPED
	assert not source.exists()


def test_given_new_file_when_wifi_upload_then_saved(tmp_path: Path):
	# given
	fs = FakeFileSystem()
	library = str(tmp_path / "lib")
	source = tmp_path / "upload.bin"
	source.write_bytes(b"photo")
	use_case = ReceiveUploadedMedia(fs)

	# when
	outcome = use_case.ingest(library, "photo.jpg", temp_path=str(source), incoming_size=5)

	# then
	assert outcome.disposition is UploadDisposition.SAVED
	dest = fs.library_path(library, LibraryFolder.ORIGINALS, "photo.jpg")
	assert fs.exists(dest)
