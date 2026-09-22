from spacemaker.application.wizard_state import wizard_actions
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.jobs import JobPhase
from spacemaker.domain.library import LibraryFolder


def test_given_wifi_and_library_when_wizard_actions_then_start_without_device():
	# given
	def count_in_folder(root: str, folder: LibraryFolder) -> int:
		return 0

	# when
	actions = wizard_actions(
		extract_phase=JobPhase.IDLE,
		convert_phase=JobPhase.IDLE,
		convert_progress_percent=0,
		library_root="/lib",
		count_in_folder=count_in_folder,
		has_device=False,
		has_source_folders=False,
		connection_method=ConnectionMethod.WIFI,
	)

	# then
	controls = actions["extract_controls"]
	assert isinstance(controls, dict)
	assert controls["start"] is True
