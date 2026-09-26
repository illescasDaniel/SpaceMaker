"""Photo backup Compress media preference (Easy).

Encode flags and folder routing stay in convert-media / adaptations;
this module only resolves the on/off preference and tools gate.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from spacemaker.domain.managed_tool import ToolResolution


# Spec: default on when tools are available and the user has never saved a choice.
DEFAULT_COMPRESS_MEDIA = True

# Both must resolve (managed or PATH) for the checkbox to be enabled.
REQUIRED_COMPRESSION_TOOL_IDS: tuple[str, ...] = ("magick", "ffmpeg")


@dataclass(frozen=True)
class CompressMediaPreference:
	"""Effective UI/session state for the Compress media control."""

	enabled: bool
	control_enabled: bool
	tools_available: bool


def compression_tools_available(resolutions: Mapping[str, ToolResolution]) -> bool:
	"""True when every required compression CLI resolves (not MISSING)."""
	return all(
		resolutions.get(tool_id, ToolResolution.MISSING) is not ToolResolution.MISSING
		for tool_id in REQUIRED_COMPRESSION_TOOL_IDS
	)


def resolve_compress_media_preference(
	*,
	stored: bool | None,
	tools_available: bool,
) -> CompressMediaPreference:
	"""Apply tools-unavailable force-off and default-on when unset.

	``stored`` is ``None`` when the user has never persisted a choice.
	When tools are missing, effective state is always off and the control is disabled,
	even if a prior "on" was stored (restored when tools return).
	"""
	if not tools_available:
		return CompressMediaPreference(
			enabled=False,
			control_enabled=False,
			tools_available=False,
		)
	effective = DEFAULT_COMPRESS_MEDIA if stored is None else stored
	return CompressMediaPreference(
		enabled=effective,
		control_enabled=True,
		tools_available=True,
	)
