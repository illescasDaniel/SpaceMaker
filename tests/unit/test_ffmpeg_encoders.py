from spacemaker.adapters.outbound.media.ffmpeg_encoders import (
	cpu_h264_encoder_ffmpeg_args,
	friendly_video_encoder_from_ffmpeg_encoders,
	hardware_video_encoder_from_ffmpeg_encoders,
)
from spacemaker.domain.gallery_batch import VideoExportEncoder
from spacemaker.domain.video_encode import HardwareVideoEncoder


def test_given_av1_nvenc_when_detect_then_av1():
	text = " V..... av1_nvenc "
	assert hardware_video_encoder_from_ffmpeg_encoders(text, vaapi_render_node=False) is HardwareVideoEncoder.AV1


def test_given_only_h264_qsv_when_detect_then_h264():
	text = " V..... h264_qsv "
	assert hardware_video_encoder_from_ffmpeg_encoders(text, vaapi_render_node=False) is HardwareVideoEncoder.H264


def test_given_no_hw_when_detect_then_none():
	assert hardware_video_encoder_from_ffmpeg_encoders("libx264", vaapi_render_node=False) is HardwareVideoEncoder.NONE


def test_given_only_libx264_when_friendly_detect_then_cpu():
	# given
	# when
	# then
	assert (
		friendly_video_encoder_from_ffmpeg_encoders("libx264", vaapi_render_node=False) is VideoExportEncoder.CPU_H264
	)


def test_given_hw_h264_and_libx264_when_friendly_detect_then_hardware_preferred():
	# given
	text = " V..... h264_nvenc  libx264"
	# when
	# then
	assert (
		friendly_video_encoder_from_ffmpeg_encoders(text, vaapi_render_node=False) is VideoExportEncoder.HARDWARE_H264
	)


def test_given_no_h264_encoder_when_friendly_detect_then_none():
	# given
	# when
	# then
	assert friendly_video_encoder_from_ffmpeg_encoders("libopus", vaapi_render_node=False) is VideoExportEncoder.NONE


def test_given_libx264_when_cpu_args_then_libx264_yuv420p_and_without_libx264_none():
	# given
	# when
	args = cpu_h264_encoder_ffmpeg_args("libx264")
	# then
	assert args is not None
	assert "libx264" in args
	assert "yuv420p" in args
	assert cpu_h264_encoder_ffmpeg_args("h264_nvenc") is None
