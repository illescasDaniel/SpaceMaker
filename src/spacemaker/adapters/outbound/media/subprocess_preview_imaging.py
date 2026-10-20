from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from spacemaker.adapters.outbound.media.exif_thumbnail import parse_exif_thumbnail
from spacemaker.adapters.outbound.media.tool_runner import ToolRunner
from spacemaker.bootstrap.bundled_tools import BundledTool
from spacemaker.domain.device_preview import DevicePreviewError, DevicePreviewErrorKind


logger = logging.getLogger(__name__)

_JPEG_QUALITY = "82"
_EMBEDDED_TIMEOUT_S = 10.0
_LIMITS = (
	"-limit", "width", "20000",
	"-limit", "height", "20000",
	"-limit", "area", "256MP",
	"-limit", "memory", "1GiB",
	"-limit", "map", "2GiB",
)  # fmt: skip
# EXIF Orientation value -> ImageMagick orientation name (the embedded thumbnail carries no tag of its own).
_ORIENTATION_NAMES = {
	2: "TopRight",
	3: "BottomRight",
	4: "BottomLeft",
	5: "LeftTop",
	6: "RightTop",
	7: "RightBottom",
	8: "LeftBottom",
}
_JPEG_SUFFIXES = {".jpg", ".jpeg"}
# Explicit Magick coder prefix per extension so content sniffing (SVG/MVG/...) can never pick the decoder.
_CODER_PREFIX = {
	".jpg": "jpeg:",
	".jpeg": "jpeg:",
	".png": "png:",
	".webp": "webp:",
	".gif": "gif:",
	".heic": "heic:",
	".heif": "heic:",
}


class SubprocessPreviewImaging:
	"""``PreviewImagingPort``: pure-Python EXIF thumbnail extraction plus Magick (subprocess) for orientation and re-encode."""

	def __init__(self, runner: ToolRunner | None = None) -> None:
		self._runner = runner or ToolRunner()

	def thumbnail_from_head(self, head: bytes, max_edge: int) -> bytes | None:
		try:
			exif = parse_exif_thumbnail(head)
			if exif is None or exif.jpeg is None:
				return None
			size = f"{max_edge}x{max_edge}"
			args = [*_LIMITS, "jpeg:-"]
			name = _ORIENTATION_NAMES.get(exif.orientation or 1)
			if name:
				args += ["-orient", name, "-auto-orient"]
			args += ["-thumbnail", f"{size}>", "-strip", "-quality", _JPEG_QUALITY, "jpeg:-"]
			output = self._run_magick(args, exif.jpeg, _EMBEDDED_TIMEOUT_S)
		except Exception:
			logger.debug("embedded thumbnail unusable", exc_info=True)
			return None
		return output or None

	def render_jpeg(self, source_path: str, max_edge: int, timeout_s: float) -> bytes:
		suffix = Path(source_path).suffix.lower()
		prefix = _CODER_PREFIX.get(suffix)
		if prefix is None:
			raise DevicePreviewError(DevicePreviewErrorKind.NO_PREVIEW, "unsupported image type")
		size = f"{max_edge}x{max_edge}"
		args = [*_LIMITS]
		if suffix in _JPEG_SUFFIXES:
			args += ["-define", f"jpeg:size={max_edge * 2}x{max_edge * 2}"]
		args += [
			f"{prefix}{source_path}[0]",
			"-auto-orient",
			"-thumbnail",
			f"{size}>",
			"-background",
			"white",
			"-alpha",
			"remove",
			"-alpha",
			"off",
			"-strip",
			"-quality",
			_JPEG_QUALITY,
			"jpeg:-",
		]
		try:
			output = self._run_magick(args, None, timeout_s)
		except subprocess.TimeoutExpired as exc:
			raise DevicePreviewError(DevicePreviewErrorKind.TIMEOUT, "image decode timed out") from exc
		except (OSError, subprocess.SubprocessError) as exc:
			raise DevicePreviewError(DevicePreviewErrorKind.NO_PREVIEW, str(exc)) from exc
		if not output:
			raise DevicePreviewError(DevicePreviewErrorKind.NO_PREVIEW, "image could not be decoded")
		return output

	def _run_magick(self, args: list[str], stdin: bytes | None, timeout_s: float) -> bytes:
		"""Run Magick and return stdout; raises on a non-zero exit (``CalledProcessError``) or timeout."""
		cmd = [str(self._runner.path(BundledTool.MAGICK)), *args]
		result = subprocess.run(  # noqa: S603
			cmd,
			input=stdin,
			capture_output=True,
			timeout=timeout_s,
			check=True,
		)
		return result.stdout
