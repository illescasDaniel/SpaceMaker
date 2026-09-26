from spacemaker.domain.compress_media import (
	DEFAULT_COMPRESS_MEDIA,
	compression_tools_available,
	resolve_compress_media_preference,
)
from spacemaker.domain.managed_tool import ToolResolution


def test_given_magick_and_ffmpeg_resolved_when_compression_tools_available_then_true():
	# given
	resolutions = {
		"magick": ToolResolution.MANAGED,
		"ffmpeg": ToolResolution.PATH,
	}

	# when / then
	assert compression_tools_available(resolutions)


def test_given_magick_missing_when_compression_tools_available_then_false():
	# given
	resolutions = {
		"magick": ToolResolution.MISSING,
		"ffmpeg": ToolResolution.MANAGED,
	}

	# when / then
	assert not compression_tools_available(resolutions)


def test_given_ffmpeg_missing_when_compression_tools_available_then_false():
	# given
	resolutions = {
		"magick": ToolResolution.PATH,
		"ffmpeg": ToolResolution.MISSING,
	}

	# when / then
	assert not compression_tools_available(resolutions)


def test_given_empty_resolutions_when_compression_tools_available_then_false():
	# given / when / then
	assert not compression_tools_available({})


def test_given_tools_available_and_never_stored_when_resolve_then_default_on():
	# given / when
	pref = resolve_compress_media_preference(stored=None, tools_available=True)

	# then
	assert pref.enabled is DEFAULT_COMPRESS_MEDIA is True
	assert pref.control_enabled is True
	assert pref.tools_available is True


def test_given_tools_available_and_stored_off_when_resolve_then_off():
	# given / when
	pref = resolve_compress_media_preference(stored=False, tools_available=True)

	# then
	assert pref.enabled is False
	assert pref.control_enabled is True
	assert pref.tools_available is True


def test_given_tools_unavailable_and_stored_on_when_resolve_then_forced_off():
	# given / when
	pref = resolve_compress_media_preference(stored=True, tools_available=False)

	# then
	assert pref.enabled is False
	assert pref.control_enabled is False
	assert pref.tools_available is False


def test_given_tools_unavailable_and_never_stored_when_resolve_then_forced_off():
	# given / when
	pref = resolve_compress_media_preference(stored=None, tools_available=False)

	# then
	assert pref.enabled is False
	assert pref.control_enabled is False
