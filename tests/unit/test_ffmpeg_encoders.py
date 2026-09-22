from spacemaker.adapters.outbound.media.ffmpeg_encoders import (
	hardware_video_encoder_from_ffmpeg_encoders,
)
from spacemaker.domain.video_encode import HardwareVideoEncoder


def test_given_av1_nvenc_when_detect_then_av1():
	text = " V..... av1_nvenc "
	assert (
		hardware_video_encoder_from_ffmpeg_encoders(text, vaapi_render_node=False)
		is HardwareVideoEncoder.AV1
	)


def test_given_only_h264_qsv_when_detect_then_h264():
	text = " V..... h264_qsv "
	assert (
		hardware_video_encoder_from_ffmpeg_encoders(text, vaapi_render_node=False)
		is HardwareVideoEncoder.H264
	)


def test_given_no_hw_when_detect_then_none():
	assert (
		hardware_video_encoder_from_ffmpeg_encoders("libx264", vaapi_render_node=False)
		is HardwareVideoEncoder.NONE
	)
