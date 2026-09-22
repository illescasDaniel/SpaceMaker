from __future__ import annotations

from spacemaker.domain.video_encode import HardwareVideoEncoder


def hardware_video_encoder_from_ffmpeg_encoders(text: str, *, vaapi_render_node: bool) -> HardwareVideoEncoder:
	if "av1_nvenc" in text or "av1_qsv" in text or ("av1_vaapi" in text and vaapi_render_node):
		return HardwareVideoEncoder.AV1
	if "h264_nvenc" in text or "h264_qsv" in text or ("h264_vaapi" in text and vaapi_render_node):
		return HardwareVideoEncoder.H264
	return HardwareVideoEncoder.NONE


def av1_encoder_ffmpeg_args(text: str, *, vaapi_render_node: bool) -> list[str] | None:
	if "av1_nvenc" in text:
		return ["-c:v", "av1_nvenc", "-preset", "p6", "-cq", "24", "-pix_fmt", "p010le"]
	if "av1_qsv" in text:
		return ["-c:v", "av1_qsv", "-global_quality", "24", "-preset", "medium", "-pix_fmt", "p010le"]
	if "av1_vaapi" in text and vaapi_render_node:
		return ["-vf", "format=p010,hwupload", "-c:v", "av1_vaapi", "-rc_mode", "CQP", "-qp", "24"]
	return None


def h264_hw_encoder_ffmpeg_args(text: str, *, vaapi_render_node: bool) -> list[str] | None:
	if "h264_nvenc" in text:
		return ["-c:v", "h264_nvenc", "-preset", "p6", "-cq", "23", "-pix_fmt", "yuv420p"]
	if "h264_qsv" in text:
		return ["-c:v", "h264_qsv", "-global_quality", "23", "-preset", "medium", "-pix_fmt", "yuv420p"]
	if "h264_vaapi" in text and vaapi_render_node:
		return [
			"-vf",
			"format=nv12,hwupload",
			"-c:v",
			"h264_vaapi",
			"-rc_mode",
			"CQP",
			"-qp",
			"23",
		]
	return None
