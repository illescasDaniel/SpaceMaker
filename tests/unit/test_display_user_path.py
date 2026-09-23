from spacemaker.bootstrap.paths import display_user_path


def test_given_path_under_home_when_display_user_path_then_uses_tilde(tmp_path, monkeypatch):
	home = tmp_path / "home"
	home.mkdir()
	monkeypatch.setattr("spacemaker.bootstrap.paths.Path.home", lambda: home)
	target = home / "Documents" / "SpaceMaker"
	target.mkdir(parents=True)

	assert display_user_path(str(target), trailing_slash=True) == "~/Documents/SpaceMaker/"
