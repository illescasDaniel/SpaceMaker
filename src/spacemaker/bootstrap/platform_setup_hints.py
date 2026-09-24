from __future__ import annotations

import sys
from typing import Any


def _windows_winget_ids(*, tools: list[dict[str, Any]]) -> list[str]:
	ids: list[str] = []
	by_tool = {str(item.get("tool_id", "")): item for item in tools}
	ffmpeg = by_tool.get("ffmpeg", {})
	if ffmpeg.get("phase") == "failed" or ffmpeg.get("resolution") == "missing":
		ids.append("Gyan.FFmpeg")
	magick = by_tool.get("magick", {})
	if magick.get("resolution") == "missing":
		ids.append("ImageMagick.ImageMagick")
	exiftool = by_tool.get("exiftool", {})
	if exiftool.get("phase") == "failed" or (
		exiftool.get("resolution") == "missing" and exiftool.get("phase") != "downloading"
	):
		ids.append("OliverBetz.ExifTool")
	seen: set[str] = set()
	ordered: list[str] = []
	for item in ids:
		if item in seen:
			continue
		seen.add(item)
		ordered.append(item)
	return ordered


def components_setup_hint(*, tools: list[dict[str, Any]] | None = None) -> dict[str, str] | None:
	"""Optional copy + install command for the Components setup screen."""
	if sys.platform != "win32":
		return None
	tool_rows = tools or []
	winget_ids = _windows_winget_ids(tools=tool_rows)
	if not winget_ids:
		return None
	command = "winget install -e " + " ".join(f"--id {package_id}" for package_id in winget_ids)
	return {
		"title": "Install missing tools with winget",
		"detail": (
			"SpaceMaker downloads adb, FFmpeg, and ExifTool when possible. ImageMagick usually needs a "
			"separate install on Windows (winget often installs under Program Files without adding PATH). "
			"Run the command below in PowerShell or Command Prompt, then click Continue in SpaceMaker."
		),
		"command": command,
	}
