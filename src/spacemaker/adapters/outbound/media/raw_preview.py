from __future__ import annotations

import subprocess
from pathlib import Path

_RAW_PREVIEW_TAGS = ("PreviewImage", "JpgFromRaw")


def extract_raw_embedded_jpeg(*, source: Path, destination: Path, exiftool: Path) -> bool:
	destination.parent.mkdir(parents=True, exist_ok=True)
	for tag in _RAW_PREVIEW_TAGS:
		result = subprocess.run(  # noqa: S603
			[str(exiftool), "-b", f"-{tag}", str(source)],
			capture_output=True,
			check=False,
		)
		if result.returncode != 0 or not result.stdout:
			continue
		destination.write_bytes(result.stdout)
		if destination.stat().st_size > 0:
			return True
		destination.unlink(missing_ok=True)
	return False


def raw_embedded_preview_available(*, source: Path, exiftool: Path) -> bool:
	for tag in _RAW_PREVIEW_TAGS:
		result = subprocess.run(  # noqa: S603
			[str(exiftool), "-b", f"-{tag}", str(source)],
			capture_output=True,
			check=False,
		)
		if result.returncode == 0 and len(result.stdout) > 0:
			return True
	return False
