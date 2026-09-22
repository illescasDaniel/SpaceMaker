from __future__ import annotations

from enum import StrEnum

from spacemaker.domain.jobs import JobPhase
from spacemaker.domain.ui_mode import UiMode


class ConvertStartPolicy(StrEnum):
	STOP_EXTRACT_FIRST = "stop_extract_first"
	CONCURRENT_WITH_EXTRACT = "concurrent_with_extract"


def convert_start_policy(*, ui_mode: UiMode) -> ConvertStartPolicy:
	if ui_mode is UiMode.EASY:
		return ConvertStartPolicy.CONCURRENT_WITH_EXTRACT
	return ConvertStartPolicy.STOP_EXTRACT_FIRST


def should_auto_drain_after_upload(
	*,
	ui_mode: UiMode,
	convert_phase: JobPhase,
	originals_count: int,
) -> bool:
	if ui_mode is not UiMode.EASY:
		return False
	if convert_phase is JobPhase.RUNNING:
		return False
	return originals_count > 0


def should_requeue_convert_drain(*, concurrent_with_extract: bool, remaining_originals: int) -> bool:
	return concurrent_with_extract and remaining_originals > 0
