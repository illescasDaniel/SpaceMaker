from __future__ import annotations

from collections.abc import Callable

from spacemaker.domain.jobs import JobPhase, can_start_convert, extract_control_flags
from spacemaker.domain.library import LibraryFolder


def originals_count_for(library_root: str, count_in_folder: Callable[[str, LibraryFolder], int]) -> int:
	if not library_root:
		return 0
	return count_in_folder(library_root, LibraryFolder.ORIGINALS)


def wizard_actions(
	*,
	extract_phase: JobPhase,
	library_root: str,
	count_in_folder: Callable[[str, LibraryFolder], int],
	has_device: bool,
	has_source_folders: bool,
) -> dict[str, object]:
	originals = originals_count_for(library_root, count_in_folder)
	controls = extract_control_flags(extract_phase)
	controls["start"] = controls["start"] and has_device and has_source_folders and bool(library_root)
	return {
		"originals_count": originals,
		"can_start_convert": can_start_convert(extract_phase=extract_phase, originals_count=originals),
		"extract_controls": controls,
	}
