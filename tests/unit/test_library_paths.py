from spacemaker.domain.library_paths import skip_media_path


def test_given_thumbnails_in_device_path_when_skip_media_path_then_true() -> None:
	assert skip_media_path("/sdcard/Pictures/.thumbnails/x.jpg")
	assert skip_media_path("DCIM/.thumbnails/foo.jpg")


def test_given_normal_path_when_skip_media_path_then_false() -> None:
	assert not skip_media_path("/sdcard/DCIM/photo.jpg")
