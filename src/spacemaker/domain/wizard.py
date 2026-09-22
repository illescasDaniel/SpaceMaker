from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from spacemaker.domain.jobs import JobPhase


class StepPhase(StrEnum):
	NOT_STARTED = "not_started"
	IN_PROGRESS = "in_progress"
	WAITING = "waiting"
	COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class WizardStepState:
	phase: StepPhase
	status_text: str
	percent: int
	can_start: bool


@dataclass(frozen=True, slots=True)
class FolderWarnings:
	error_count: int
	invalid_count: int

	@property
	def has_error_warning(self) -> bool:
		return self.error_count > 0

	@property
	def has_invalid_warning(self) -> bool:
		return self.invalid_count > 0


def convert_step_state(
	*,
	extract_complete: bool,
	convert_running: bool,
	convert_complete: bool,
	progress_percent: int,
) -> WizardStepState:
	if convert_running:
		return WizardStepState(
			phase=StepPhase.IN_PROGRESS,
			status_text=f"In progress: {progress_percent}%",
			percent=progress_percent,
			can_start=False,
		)
	if convert_complete:
		return WizardStepState(
			phase=StepPhase.COMPLETED,
			status_text="Completed",
			percent=100,
			can_start=False,
		)
	if extract_complete:
		return WizardStepState(
			phase=StepPhase.NOT_STARTED,
			status_text="Ready",
			percent=0,
			can_start=True,
		)
	return WizardStepState(
		phase=StepPhase.WAITING,
		status_text="Waiting for extract to finish",
		percent=0,
		can_start=False,
	)


def visualize_step_state(
	*,
	converted_count: int,
	convert_phase: JobPhase,
	progress_percent: int,
) -> WizardStepState:
	if convert_phase is JobPhase.RUNNING:
		return WizardStepState(
			phase=StepPhase.IN_PROGRESS,
			status_text=f"In progress: {progress_percent}%",
			percent=progress_percent,
			can_start=True,
		)
	if converted_count > 0:
		label = "file" if converted_count == 1 else "files"
		return WizardStepState(
			phase=StepPhase.COMPLETED,
			status_text=f"Ready: {converted_count} {label}",
			percent=100,
			can_start=True,
		)
	return WizardStepState(
		phase=StepPhase.NOT_STARTED,
		status_text="Not started",
		percent=0,
		can_start=False,
	)
