from tests.unit.fakes import FakeDeviceRepository, FakeFileSystem

from spacemaker.application.extract_media import ExtractMedia
from spacemaker.domain.library import LibraryFolder, TransferMode
from spacemaker.ports.outbound.device_repository import DeviceInfo


def test_given_existing_original_with_same_size_when_extract_then_skips_pull():
	# given
	fs = FakeFileSystem()
	devices = FakeDeviceRepository()
	devices.bind_filesystem(fs)
	devices.devices = [DeviceInfo(device_id="dev1", label="Pixel")]
	devices.media_paths = ["/DCIM/photo.jpg"]
	devices.sizes["/DCIM/photo.jpg"] = 500
	library = "/lib"
	dest = fs.library_path(library, LibraryFolder.ORIGINALS, "DCIM/photo.jpg")
	fs.files[dest] = 500
	use_case = ExtractMedia(devices, fs)
	# when
	result = use_case.run(library, "dev1", TransferMode.COPY)
	# then
	assert result.completed == 1
	assert len(devices.pulled) == 0


def test_given_thumbnails_path_when_extract_then_skips_pull():
	fs = FakeFileSystem()
	devices = FakeDeviceRepository()
	devices.bind_filesystem(fs)
	devices.devices = [DeviceInfo(device_id="dev1", label="Pixel")]
	devices.media_paths = ["/Pictures/.thumbnails/preview.jpg", "/Pictures/photo.jpg"]
	devices.sizes["/Pictures/photo.jpg"] = 120
	use_case = ExtractMedia(devices, fs)
	result = use_case.run("/lib", "dev1", TransferMode.COPY)
	assert result.total == 1
	assert len(devices.pulled) == 1
	assert devices.pulled[0][1] == "/Pictures/photo.jpg"


def test_given_copy_mode_when_extract_then_file_stays_on_device():
	# given
	fs = FakeFileSystem()
	devices = FakeDeviceRepository()
	devices.bind_filesystem(fs)
	devices.devices = [DeviceInfo(device_id="dev1", label="Pixel")]
	devices.media_paths = ["/DCIM/photo.jpg"]
	devices.sizes["/DCIM/photo.jpg"] = 120
	use_case = ExtractMedia(devices, fs)
	# when
	use_case.run("/lib", "dev1", TransferMode.COPY)
	# then
	assert devices.deleted == []
