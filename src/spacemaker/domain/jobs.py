from __future__ import annotations

from enum import StrEnum


class JobPhase(StrEnum):
	IDLE = "idle"
	RUNNING = "running"
	PAUSED = "paused"
	DONE = "done"
	STOPPED = "stopped"
	ERROR = "error"


def can_start_convert(*, originals_count: int, convert_job_active: bool = False) -> bool:
	if convert_job_active:
		return False
	return originals_count > 0


def extract_control_flags(extract_phase: JobPhase) -> dict[str, bool]:
	return {
		"start": extract_phase in {JobPhase.IDLE, JobPhase.DONE, JobPhase.STOPPED, JobPhase.ERROR},
		"pause": extract_phase is JobPhase.RUNNING,
		"resume": extract_phase is JobPhase.PAUSED,
		"stop": extract_phase in {JobPhase.RUNNING, JobPhase.PAUSED},
	}


def convert_control_flags(convert_phase: JobPhase) -> dict[str, bool]:
	return {
		"start": convert_phase in {JobPhase.IDLE, JobPhase.DONE, JobPhase.STOPPED, JobPhase.ERROR},
		"stop": convert_phase is JobPhase.RUNNING,
	}
