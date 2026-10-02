from spacemaker.domain.upload_paths import is_safe_upload_relative_path, normalize_upload_relative_path


def test_given_dotdot_when_normalize_then_none():
	assert normalize_upload_relative_path("../secret.jpg") is None
	assert is_safe_upload_relative_path("../x") is False


def test_given_relative_path_when_normalize_then_posix():
	assert normalize_upload_relative_path("DCIM/Camera/a.jpg") == "DCIM/Camera/a.jpg"


def test_given_windows_drive_path_when_checked_then_unsafe():
	# given
	paths = ["C:/Windows/evil.jpg", "C:evil.jpg"]
	# when
	results = [is_safe_upload_relative_path(path) for path in paths]
	normalized = normalize_upload_relative_path("D:\\x\\a.jpg")
	# then
	assert results == [False, False]
	assert normalized is None
