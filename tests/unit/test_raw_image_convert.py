from pathlib import Path

from spacemaker.adapters.outbound.filesystem.local import LocalFileSystem
from spacemaker.adapters.outbound.media.subprocess_converter import SubprocessMediaConverter
from spacemaker.adapters.outbound.media.subprocess_probe import SubprocessMediaProbe
from spacemaker.adapters.outbound.media.tool_runner import ToolRunner
from spacemaker.application.convert_media import ConvertMedia
from spacemaker.domain.library import LibraryFolder


def _install_tool_scripts(tools: Path) -> None:
	magick = tools / "magick"
	magick.write_text(
		"#!/bin/sh\n"
		'if [ "$1" = "identify" ]; then\n'
		'  case "$3" in *.dng) exit 1 ;; esac\n'
		"  exit 0\n"
		"fi\n"
		'if [ "$1" = "-version" ]; then exit 0; fi\n'
		'dest="${@: -1}"\n'
		'echo "fake-avif" > "$dest"\n'
		"exit 0\n",
	)
	magick.chmod(0o755)
	exiftool = tools / "exiftool"
	exiftool.write_text(
		"#!/bin/sh\n"
		'if [ "$1" = "-b" ] && [ "$2" = "-PreviewImage" ]; then\n'
		"  printf '\\xff\\xd8\\xff\\xdbpreview'\n"
		"  exit 0\n"
		"fi\n"
		"exit 1\n",
	)
	exiftool.chmod(0o755)


def test_given_dng_when_magick_cannot_read_then_converts_embedded_preview(tmp_path: Path) -> None:
	tools = tmp_path / "tools"
	tools.mkdir()
	_install_tool_scripts(tools)
	library = tmp_path / "lib"
	rel = "IMG_5163.dng"
	original = library / "originals" / rel
	original.parent.mkdir(parents=True)
	original.write_bytes(b"fake-dng")
	fs = LocalFileSystem()
	runner = ToolRunner(bundle_root_path=tools, platform_is_windows=False)
	probe = SubprocessMediaProbe(runner)
	converter = SubprocessMediaConverter(runner)
	use_case = ConvertMedia(fs, converter, probe)
	use_case.run(str(library))
	dest = fs.library_path(str(library), LibraryFolder.CONVERTED, "IMG_5163.avif")
	assert Path(dest).is_file()
	assert not Path(fs.library_path(str(library), LibraryFolder.ORIGINALS, rel)).exists()
	assert not Path(fs.library_path(str(library), LibraryFolder.INVALID, rel)).exists()
