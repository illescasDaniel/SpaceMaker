from spacemaker.domain.conversion import (
	image_avif_relative_path,
	output_exceeds_rollback_threshold,
	route_before_encode,
)
from spacemaker.domain.web_compat import VideoProbe


def test_given_jpeg_when_collision_avif_exists_then_planned_path_uses_ext_suffix():
	# given
	rel = "2024/photo.jpg"
	# when
	out = image_avif_relative_path(rel, collision_avif_exists=True)
	# then
	assert out == "2024/photo_jpg.avif"


def test_given_web_av1_video_when_route_then_move_as_is():
	# given
	probe = VideoProbe(container_ext="mp4", video_codec="av1", audio_codec="aac", bitrate_bps=2_000_000)
	# when
	route = route_before_encode("clip.mp4", video_probe=probe)
	# then
	from spacemaker.domain.conversion import ConversionRoute

	assert route is ConversionRoute.MOVE_AS_IS


def test_given_output_size_above_110_percent_when_check_then_rollback():
	# given
	source_size = 1000
	output_size = 1101
	# when
	# then
	assert output_exceeds_rollback_threshold(source_size, output_size) is True
