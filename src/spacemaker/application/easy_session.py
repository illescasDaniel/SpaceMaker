from __future__ import annotations

from spacemaker.domain.app_module import AppModule
from spacemaker.domain.jobs import JobPhase
from spacemaker.domain.ui_mode import UiMode


def should_auto_start_wifi_extract(
	*,
	active_module: AppModule,
	ui_mode: UiMode,
	extract_phase: JobPhase,
	library_root: str,
) -> bool:
	if active_module is not AppModule.PHOTO_BACKUP:
		return False
	if ui_mode is not UiMode.EASY:
		return False
	if not library_root:
		return False
	return extract_phase in {JobPhase.IDLE, JobPhase.DONE, JobPhase.STOPPED, JobPhase.ERROR}
