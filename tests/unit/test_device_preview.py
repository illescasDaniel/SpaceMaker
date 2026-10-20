from dataclasses import replace

import pytest

from spacemaker.domain import device_preview
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.device_preview import (
	PREVIEWABLE_IMAGE_EXTENSIONS,
	DevicePreviewKind,
	DevicePreviewRequest,
	device_preview_cache_key,
	is_previewable_image,
)


def _request() -> DevicePreviewRequest:
	return DevicePreviewRequest(
		method=ConnectionMethod.ADB,
		device_id="dev1",
		path="DCIM/Camera/IMG_0001.jpg",
		size=4_000_000,
		mtime=1_700_000_000,
		kind=DevicePreviewKind.THUMB,
	)


def test_given_thumb_kind_when_max_edge_then_320() -> None:
	# given
	kind = DevicePreviewKind.THUMB
	# when
	edge = kind.max_edge
	# then
	assert edge == 320


def test_given_preview_kind_when_max_edge_then_1600() -> None:
	# given
	kind = DevicePreviewKind.PREVIEW
	# when
	edge = kind.max_edge
	# then
	assert edge == 1600


def test_given_spec_formats_when_listing_extensions_then_exactly_the_seven() -> None:
	# given
	# when
	extensions = PREVIEWABLE_IMAGE_EXTENSIONS
	# then
	assert extensions == {"jpg", "jpeg", "png", "webp", "gif", "heic", "heif"}


@pytest.mark.parametrize("extension", ["jpg", "jpeg", "png", "webp", "gif", "heic", "heif"])
def test_given_image_extension_when_is_previewable_then_true(extension: str) -> None:
	# given
	name = f"IMG_0001.{extension}"
	# when
	result = is_previewable_image(name)
	# then
	assert result is True


@pytest.mark.parametrize("name", ["IMG_0001.JPG", "photo.JpEg", "SCAN.HEIC", "a.b.c.PNG"])
def test_given_mixed_case_name_when_is_previewable_then_true(name: str) -> None:
	# given
	# when
	result = is_previewable_image(name)
	# then
	assert result is True


@pytest.mark.parametrize("name", ["clip.mp4", "IMG_0001.dng", "README", "jpg", "photo.jpg.mp4", "notes.txt", ""])
def test_given_other_name_when_is_previewable_then_false(name: str) -> None:
	# given
	# when
	result = is_previewable_image(name)
	# then
	assert result is False


def test_given_same_request_when_cache_key_twice_then_equal_hex() -> None:
	# given
	request = _request()
	# when
	first = device_preview_cache_key(request)
	second = device_preview_cache_key(replace(request))
	# then
	assert first == second
	assert first
	assert all(char in "0123456789abcdef" for char in first)


@pytest.mark.parametrize(
	"change",
	[
		{"method": ConnectionMethod.AFC},
		{"device_id": "dev2"},
		{"path": "DCIM/Camera/IMG_0002.jpg"},
		{"size": 4_000_001},
		{"mtime": 1_700_000_001},
		{"kind": DevicePreviewKind.PREVIEW},
	],
)
def test_given_one_field_changed_when_cache_key_then_differs(change: dict[str, object]) -> None:
	# given
	request = _request()
	# when
	changed = device_preview_cache_key(replace(request, **change))  # type: ignore[arg-type]
	# then
	assert changed != device_preview_cache_key(request)


def test_given_new_format_version_when_cache_key_then_old_key_no_longer_matches(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	# given
	request = _request()
	before = device_preview_cache_key(request)
	# when
	monkeypatch.setattr(device_preview, "DEVICE_PREVIEW_FORMAT_VERSION", "next-version")
	after = device_preview_cache_key(request)
	# then
	assert after != before


# Video posters: the format version moved to "2" so v1 (photo-only) cache entries are a miss.
def test_given_video_posters_release_when_cache_key_then_version_2_and_v1_key_differs(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	# given
	request = _request()
	current = device_preview_cache_key(request)
	version = device_preview.DEVICE_PREVIEW_FORMAT_VERSION
	# when
	monkeypatch.setattr(device_preview, "DEVICE_PREVIEW_FORMAT_VERSION", "1")
	v1_key = device_preview_cache_key(request)
	# then
	assert version == "2"
	assert v1_key != current
