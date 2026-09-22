from __future__ import annotations

from collections.abc import Callable

from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.jobs import JobPhase, can_start_convert, extract_control_flags
from spacemaker.domain.library import LibraryFolder
from spacemaker.domain.wizard import visualize_step_state


def originals_count_for(library_root: str, count_in_folder: Callable[[str, LibraryFolder], int]) -> int:
	if not library_root:
		return 0
	return count_in_folder(library_root, LibraryFolder.ORIGINALS)


def wizard_actions(
	*,
	extract_phase: JobPhase,
	convert_phase: JobPhase,
	convert_progress_percent: int,
	library_root: str,
	count_in_folder: Callable[[str, LibraryFolder], int],
	has_device: bool,
	has_source_folders: bool,
	connection_method: ConnectionMethod = ConnectionMethod.WIFI,
) -> dict[str, object]:
	originals = originals_count_for(library_root, count_in_folder)
	converted = count_in_folder(library_root, LibraryFolder.CONVERTED) if library_root else 0
	controls = extract_control_flags(extract_phase)
	if connection_method is ConnectionMethod.WIFI:
		controls["start"] = controls["start"] and bool(library_root)
	else:
		controls["start"] = controls["start"] and has_device and has_source_folders and bool(library_root)
	visualize = visualize_step_state(
		converted_count=converted,
		convert_phase=convert_phase,
		progress_percent=convert_progress_percent,
	)
	return {
		"originals_count": originals,
		"can_start_convert": can_start_convert(extract_phase=extract_phase, originals_count=originals),
		"extract_controls": controls,
		"visualize": {
			"phase": visualize.phase.value,
			"status_text": visualize.status_text,
			"percent": visualize.percent,
			"enabled": visualize.can_start,
		},
	}
