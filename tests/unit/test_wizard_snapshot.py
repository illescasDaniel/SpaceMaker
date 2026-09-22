from spacemaker.application.wizard_state import wizard_actions
from spacemaker.domain.jobs import JobPhase
from spacemaker.domain.library import LibraryFolder


def test_given_converted_count_when_wizard_actions_then_visualize_enabled():
	# given
	def count_in_folder(root: str, folder: LibraryFolder) -> int:
		if folder is LibraryFolder.CONVERTED:
			return 3
		return 0

	# when
	actions = wizard_actions(
		extract_phase=JobPhase.DONE,
		convert_phase=JobPhase.IDLE,
		convert_progress_percent=0,
		library_root="/lib",
		count_in_folder=count_in_folder,
		has_device=True,
		has_source_folders=True,
	)
	# then
	visualize = actions["visualize"]
	assert isinstance(visualize, dict)
	assert visualize["enabled"] is True
	assert "3" in str(visualize["status_text"])
