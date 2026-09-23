from spacemaker.application.easy_session import should_auto_start_wifi_extract
from spacemaker.domain.app_module import AppModule
from spacemaker.domain.jobs import JobPhase
from spacemaker.domain.ui_mode import UiMode


def test_given_photo_backup_easy_idle_and_library_when_should_auto_start_wifi_then_true():
	assert should_auto_start_wifi_extract(
		active_module=AppModule.PHOTO_BACKUP,
		ui_mode=UiMode.EASY,
		extract_phase=JobPhase.IDLE,
		library_root="/home/user/Pictures/SpaceMakerLibrary",
	)


def test_given_home_module_when_should_auto_start_wifi_then_false():
	assert not should_auto_start_wifi_extract(
		active_module=AppModule.HOME,
		ui_mode=UiMode.EASY,
		extract_phase=JobPhase.IDLE,
		library_root="/home/user/Pictures/SpaceMakerLibrary",
	)


def test_given_advanced_when_should_auto_start_wifi_then_false():
	assert not should_auto_start_wifi_extract(
		active_module=AppModule.PHOTO_BACKUP,
		ui_mode=UiMode.ADVANCED,
		extract_phase=JobPhase.IDLE,
		library_root="/home/user/Pictures/SpaceMakerLibrary",
	)
