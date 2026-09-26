from spacemaker.adapters.outbound.preferences.json_store import JsonUserPreferences


def test_given_missing_file_when_get_compress_media_then_none(tmp_path):
	# given
	prefs = JsonUserPreferences(tmp_path / "preferences.json")

	# when / then
	assert prefs.get_compress_media() is None


def test_given_set_false_when_get_compress_media_then_false(tmp_path):
	# given
	path = tmp_path / "preferences.json"
	prefs = JsonUserPreferences(path)

	# when
	prefs.set_compress_media(False)

	# then
	assert prefs.get_compress_media() is False
	assert path.is_file()


def test_given_set_true_when_reloaded_then_persists(tmp_path):
	# given
	path = tmp_path / "preferences.json"
	JsonUserPreferences(path).set_compress_media(True)

	# when
	reloaded = JsonUserPreferences(path)

	# then
	assert reloaded.get_compress_media() is True


def test_given_corrupt_json_when_get_compress_media_then_none(tmp_path):
	# given
	path = tmp_path / "preferences.json"
	path.write_text("{not-json", encoding="utf-8")
	prefs = JsonUserPreferences(path)

	# when / then
	assert prefs.get_compress_media() is None


def test_given_other_keys_when_set_compress_media_then_preserves_them(tmp_path):
	# given
	path = tmp_path / "preferences.json"
	path.write_text('{"other": 1}\n', encoding="utf-8")
	prefs = JsonUserPreferences(path)

	# when
	prefs.set_compress_media(False)

	# then
	assert prefs.get_compress_media() is False
	raw = path.read_text(encoding="utf-8")
	assert '"other"' in raw
