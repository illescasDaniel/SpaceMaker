from spacemaker.domain.video_encode import is_inline_preview_video
from spacemaker.domain.web_compat import VideoProbe


def test_given_hevc_mp4_when_preview_check_then_false():
	probe = VideoProbe("mp4", "hevc", "aac", 2_000_000)
	assert is_inline_preview_video(probe) is False


def test_given_h264_mp4_when_preview_check_then_true():
	probe = VideoProbe("mp4", "h264", "aac", 2_000_000)
	assert is_inline_preview_video(probe) is True
