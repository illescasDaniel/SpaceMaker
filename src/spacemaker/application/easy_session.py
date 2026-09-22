from __future__ import annotations

from spacemaker.domain.jobs import JobPhase
from spacemaker.domain.ui_mode import UiMode


def should_auto_start_wifi_extract(
	*,
	ui_mode: UiMode,
	extract_phase: JobPhase,
	library_root: str,
) -> bool:
	if ui_mode is not UiMode.EASY:
		return False
	if not library_root:
		return False
	return extract_phase in {JobPhase.IDLE, JobPhase.DONE, JobPhase.STOPPED, JobPhase.ERROR}
