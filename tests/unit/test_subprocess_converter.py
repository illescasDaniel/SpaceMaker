from pathlib import Path

from tests.unit.fakes import FakeMediaProbe

from spacemaker.adapters.outbound.filesystem.local import LocalFileSystem
from spacemaker.application.convert_media import ConvertMedia
from spacemaker.domain.library import LibraryFolder


class RecordingConverter:
	def __init__(self) -> None:
		self.destinations: list[str] = []

	def library_video_encoder(self):
		from spacemaker.domain.video_encode import HardwareVideoEncoder

		return HardwareVideoEncoder.AV1

	def encode_image_to_avif(self, source: str, destination: str) -> None:
		self.destinations.append(destination)
		Path(destination).write_bytes(b"fake-avif")

	def encode_video_to_av1(self, source: str, destination: str) -> None:
		self.destinations.append(destination)


def test_given_nested_original_when_convert_then_creates_converted_parent(tmp_path: Path) -> None:
	library = tmp_path / "lib"
	rel = "sdcard/Pictures/photo.webp"
	original = library / "originals" / rel
	original.parent.mkdir(parents=True)
	original.write_bytes(b"RIFFxxxxWEBP")

	fs = LocalFileSystem()
	src = fs.library_path(str(library), LibraryFolder.ORIGINALS, rel)
	dest = fs.library_path(str(library), LibraryFolder.CONVERTED, "sdcard/Pictures/photo.avif")
	converter = RecordingConverter()
	probe = FakeMediaProbe()
	probe.readable_images.add(src)
	probe.valid_images.add(dest)
	use_case = ConvertMedia(fs, converter, probe)
	use_case.run(str(library))

	assert Path(dest).is_file()
	assert dest in converter.destinations
