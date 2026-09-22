from __future__ import annotations

from enum import StrEnum


class JobPhase(StrEnum):
	IDLE = "idle"
	RUNNING = "running"
	PAUSED = "paused"
	DONE = "done"
	STOPPED = "stopped"
	ERROR = "error"


def can_start_convert(*, extract_phase: JobPhase, originals_count: int) -> bool:
	if extract_phase in {JobPhase.RUNNING, JobPhase.PAUSED}:
		return False
	return originals_count > 0


def extract_control_flags(extract_phase: JobPhase) -> dict[str, bool]:
	return {
		"start": extract_phase in {JobPhase.IDLE, JobPhase.DONE, JobPhase.STOPPED, JobPhase.ERROR},
		"pause": extract_phase is JobPhase.RUNNING,
		"resume": extract_phase is JobPhase.PAUSED,
		"stop": extract_phase in {JobPhase.RUNNING, JobPhase.PAUSED},
	}
