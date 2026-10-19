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


def test_given_extras_when_extract_then_only_media_under_extras_are_pulled():
	# given
	fs = FakeFileSystem()
	devices = FakeDeviceRepository()
	devices.bind_filesystem(fs)
	devices.devices = [DeviceInfo(device_id="dev1", label="Pixel")]
	devices.file_paths = [
		"/sdcard/WhatsApp/Media/IMG-1.jpg",
		"/sdcard/WhatsApp/Media/VID-1.mp4",
		"/sdcard/WhatsApp/Media/ticket.pdf",
		"/sdcard/Other/skip.jpg",
	]
	use_case = ExtractMedia(devices, fs)
	# when
	result = use_case.run(
		"/lib",
		"dev1",
		TransferMode.COPY,
		source_folders=frozenset(),
		extra_paths=frozenset({"WhatsApp/Media"}),
	)
	# then
	assert result.total == 2
	assert sorted(p[1] for p in devices.pulled) == [
		"/sdcard/WhatsApp/Media/IMG-1.jpg",
		"/sdcard/WhatsApp/Media/VID-1.mp4",
	]


def test_given_presets_and_extras_when_extract_then_union_without_duplicates():
	# given
	fs = FakeFileSystem()
	devices = FakeDeviceRepository()
	devices.bind_filesystem(fs)
	devices.devices = [DeviceInfo(device_id="dev1", label="Pixel")]
	devices.media_paths = ["/sdcard/DCIM/a.jpg"]
	devices.file_paths = ["/sdcard/DCIM/a.jpg", "/sdcard/WhatsApp/Media/b.jpg"]
	use_case = ExtractMedia(devices, fs)
	# when
	result = use_case.run(
		"/lib",
		"dev1",
		TransferMode.COPY,
		extra_paths=frozenset({"DCIM", "WhatsApp/Media"}),
	)
	# then
	assert result.total == 2
