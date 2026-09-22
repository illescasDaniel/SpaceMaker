from spacemaker.domain.upload_paths import is_safe_upload_relative_path, normalize_upload_relative_path


def test_given_dotdot_when_normalize_then_none():
	assert normalize_upload_relative_path("../secret.jpg") is None
	assert is_safe_upload_relative_path("../x") is False


def test_given_relative_path_when_normalize_then_posix():
	assert normalize_upload_relative_path("DCIM/Camera/a.jpg") == "DCIM/Camera/a.jpg"
