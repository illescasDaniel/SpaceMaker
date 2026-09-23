from spacemaker import __version__
from spacemaker.bootstrap.app_meta import APP_AUTHOR, APP_CONTACT_EMAIL, app_release_info


def test_given_installed_package_when_reading_release_info_then_matches_1_0():
	info = app_release_info()
	assert __version__ == "1.0.0"
	assert info["app_version"] == "1.0.0"
	assert info["app_author"] == APP_AUTHOR
	assert info["app_contact"] == APP_CONTACT_EMAIL
	assert APP_AUTHOR == "Daniel Illescas Romero"
	assert APP_CONTACT_EMAIL == "contact@daniel-ir.eu"
