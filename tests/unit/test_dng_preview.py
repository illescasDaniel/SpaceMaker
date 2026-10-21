import random

import pytest
from tests.unit.dng_builder import JPEG, DngFile, build_dng, jpeg_ifd

from spacemaker.domain.dng_preview import (
	DNG_HEADER_READ_BYTES,
	DNG_MAX_PREVIEW_BYTES,
	DNG_MAX_SUBIFDS,
	DngPreviewCandidate,
	DngPreviewLocation,
	ImageContainer,
	locate_dng_preview,
	pick_dng_preview,
	sniff_container,
)


ORDERS = ["<", ">"]
PREVIEW_AT = 5000
RAW_ENTRIES = {  # a CFA raw SubIFD: never a candidate
	0x00FE: ("I", [0]),
	0x0100: ("I", [4000]),
	0x0101: ("I", [3000]),
	0x0102: ("H", [16]),
	0x0103: ("H", [7]),
	0x0106: ("H", [32803]),
	0x0111: ("I", [PREVIEW_AT]),
	0x0117: ("I", [len(JPEG)]),
}


def _locate(dng: DngFile) -> DngPreviewLocation | None:
	return locate_dng_preview(dng.head, dng.size, dng.read_at)


def _pixel(order: str, orientation: int = 6, **kwargs: object) -> DngFile:
	entries = jpeg_ifd(1280, 960, PREVIEW_AT, len(JPEG), orientation=orientation)
	return build_dng(order, [(8, entries)], jpeg_at=PREVIEW_AT, **kwargs)  # type: ignore[arg-type]


def _candidate(edge: int) -> DngPreviewCandidate:
	return DngPreviewCandidate(100, 10, edge, edge * 3 // 4)


# sniff_container


@pytest.mark.parametrize(
	("head", "expected"),
	[
		(b"\xff\xd8\xff\xe1xx", ImageContainer.JPEG),
		(b"II*\x00\x08\x00\x00\x00", ImageContainer.TIFF),
		(b"MM\x00*\x00\x00\x00\x08", ImageContainer.TIFF),
		(b"\x89PNG", ImageContainer.UNKNOWN),
		(b"II*", ImageContainer.UNKNOWN),
		(b"", ImageContainer.UNKNOWN),
	],
)
def test_given_first_bytes_when_sniff_then_container(head: bytes, expected: ImageContainer) -> None:
	# given / when
	result = sniff_container(head)
	# then
	assert result is expected


# pick_dng_preview


def test_given_320_1024_4000_when_pick_then_1024() -> None:
	# given
	candidates = [_candidate(320), _candidate(1024), _candidate(4000)]
	# when
	picked = pick_dng_preview(candidates)
	# then
	assert picked == candidates[1]


def test_given_only_4032_when_pick_then_that_one() -> None:
	# given
	candidates = [_candidate(4032)]
	# when / then
	assert pick_dng_preview(candidates) == candidates[0]


def test_given_all_larger_than_limit_when_pick_then_smallest_of_them() -> None:
	# given
	candidates = [_candidate(4000), _candidate(2400), _candidate(3000)]
	# when / then
	assert pick_dng_preview(candidates) == candidates[1]


def test_given_tie_when_pick_then_first_in_ifd_order() -> None:
	# given
	first, second = DngPreviewCandidate(1, 1, 1000, 500), DngPreviewCandidate(2, 1, 500, 1000)
	# when / then
	assert pick_dng_preview([first, second]) is first


def test_given_no_candidates_when_pick_then_none() -> None:
	# given / when
	result = pick_dng_preview([])
	# then
	assert result is None


# locate_dng_preview: real-world layouts


@pytest.mark.parametrize("order", ORDERS)
def test_given_pixel_layout_when_locate_then_ifd0_preview_without_extra_reads(order: str) -> None:
	# given
	dng = _pixel(order)
	# when
	location = _locate(dng)
	# then
	assert location == DngPreviewLocation(PREVIEW_AT, len(JPEG), 1280, 960, 6)
	assert dng.reads == []


@pytest.mark.parametrize("order", ORDERS)
def test_given_ifd0_near_end_of_file_when_locate_then_exactly_one_read_at_ifd0(order: str) -> None:
	# given
	ifd0_at = 20_000
	entries = jpeg_ifd(1280, 960, PREVIEW_AT, len(JPEG), orientation=8)
	dng = build_dng(order, [(ifd0_at, entries)], jpeg_at=PREVIEW_AT)
	# when
	location = _locate(dng)
	# then
	assert location == DngPreviewLocation(PREVIEW_AT, len(JPEG), 1280, 960, 8)
	assert len(dng.reads) == 1
	assert dng.reads[0][0] == ifd0_at
	assert dng.reads[0][1] == min(DNG_HEADER_READ_BYTES, dng.size - ifd0_at)


@pytest.mark.parametrize("order", ORDERS)
def test_given_tail_ifd0_with_bits_per_sample_stored_far_away_when_locate_then_ifd0_without_more_reads(
	order: str,
) -> None:
	# given: Pixel tail layout: IFD0 ~6 KB before EOF, its out-of-line values ~1.77 MB in, a raw SubIFD
	ifd0_at = 2_000_000
	raw_at = 1_800_000
	entries = jpeg_ifd(1280, 960, PREVIEW_AT, len(JPEG), orientation=6, subfile_type=1, sub_ifds=[raw_at])
	raw = jpeg_ifd(4032, 3024, 3_000_000, 1000, photometric=32803, subfile_type=0)
	dng = build_dng(
		order, [(ifd0_at, entries), (raw_at, raw)], jpeg_at=PREVIEW_AT, size=ifd0_at + 6000, ifd0_values_at=1_770_000
	)
	# when
	location = _locate(dng)
	# then
	assert location == DngPreviewLocation(PREVIEW_AT, len(JPEG), 1280, 960, 6)
	assert [offset for offset, _ in dng.reads] == [ifd0_at]


def test_given_no_bits_per_sample_when_locate_then_none() -> None:
	# given
	entries = jpeg_ifd(1280, 960, PREVIEW_AT, len(JPEG))
	del entries[0x0102]
	dng = build_dng("<", [(8, entries)], jpeg_at=PREVIEW_AT)
	# when / then
	assert _locate(dng) is None


def test_given_iphone_big_endian_layout_when_locate_then_preview_and_ifd0_orientation() -> None:
	# given
	entries = jpeg_ifd(4032, 3024, PREVIEW_AT, len(JPEG), orientation=6)
	dng = build_dng(">", [(8, entries)], jpeg_at=PREVIEW_AT, size=52 * 1024 * 1024)
	# when
	location = _locate(dng)
	# then
	assert location == DngPreviewLocation(PREVIEW_AT, len(JPEG), 4032, 3024, 6)


@pytest.mark.parametrize("order", ORDERS)
def test_given_ifd0_is_uncompressed_thumb_when_locate_then_subifd_preview_and_raw_not_chosen(order: str) -> None:
	# given
	thumb = {
		0x0100: ("I", [256]),
		0x0101: ("I", [171]),
		0x0102: ("H", [8, 8, 8]),
		0x0103: ("H", [1]),
		0x0106: ("H", [2]),
		0x0112: ("H", [3]),
		0x014A: ("I", [1000, 2000]),
	}
	preview = jpeg_ifd(1024, 683, PREVIEW_AT, len(JPEG), subfile_type=1)
	dng = build_dng(order, [(8, thumb), (1000, preview), (2000, RAW_ENTRIES)], jpeg_at=PREVIEW_AT)
	# when
	location = _locate(dng)
	# then
	assert location == DngPreviewLocation(PREVIEW_AT, len(JPEG), 1024, 683, 3)
	assert [offset for offset, _ in dng.reads] == [1000, 2000]


def test_given_single_subifd_stored_inline_when_locate_then_found() -> None:
	# given
	thumb = {0x0103: ("H", [1]), 0x014A: ("I", [1000])}
	preview = jpeg_ifd(1024, 683, PREVIEW_AT, len(JPEG), strip=False)
	dng = build_dng("<", [(8, thumb), (1000, preview)], jpeg_at=PREVIEW_AT)
	# when / then
	location = _locate(dng)
	assert location is not None
	assert location.offset == PREVIEW_AT


def test_given_several_previews_in_subifds_when_locate_then_largest_within_1600() -> None:
	# given
	thumb = {0x014A: ("I", [1000, 2000, 3000])}
	ifds = [
		(8, thumb),
		(1000, jpeg_ifd(320, 213, 4000, len(JPEG))),
		(2000, jpeg_ifd(1024, 683, 4100, len(JPEG))),
		(3000, jpeg_ifd(4000, 3000, 4200, len(JPEG))),
	]
	dng = build_dng("<", ifds, jpeg_at=4000, size=10_000)
	# when
	location = _locate(dng)
	# then
	assert location is not None
	assert (location.width, location.height) == (1024, 683)


# locate_dng_preview: things that are not previews


def test_given_mask_subfile_type_when_locate_then_none() -> None:
	# given
	entries = jpeg_ifd(1280, 960, PREVIEW_AT, len(JPEG), subfile_type=65540)
	dng = build_dng("<", [(8, entries)], jpeg_at=PREVIEW_AT)
	# when / then
	assert _locate(dng) is None


def test_given_jpeg_xl_tiles_when_locate_then_none_without_image_reads() -> None:
	# given
	entries = jpeg_ifd(1280, 960, PREVIEW_AT, len(JPEG), compression=52546)
	dng = build_dng("<", [(8, entries)], jpeg_at=PREVIEW_AT)
	# when / then
	assert _locate(dng) is None
	assert dng.reads == []


def test_given_16_bit_samples_when_locate_then_none() -> None:
	# given
	entries = jpeg_ifd(1280, 960, PREVIEW_AT, len(JPEG))
	entries[0x0102] = ("H", [8, 8, 16])
	dng = build_dng("<", [(8, entries)], jpeg_at=PREVIEW_AT)
	# when / then
	assert _locate(dng) is None


def test_given_invalid_orientation_when_locate_then_one() -> None:
	# given
	dng = _pixel("<", orientation=42)
	# when
	location = _locate(dng)
	# then
	assert location is not None
	assert location.orientation == 1


def test_given_no_orientation_when_locate_then_one() -> None:
	# given
	entries = jpeg_ifd(1280, 960, PREVIEW_AT, len(JPEG))
	dng = build_dng("<", [(8, entries)], jpeg_at=PREVIEW_AT)
	# when / then
	location = _locate(dng)
	assert location is not None
	assert location.orientation == 1


# locate_dng_preview: malformed input


def test_given_truncated_header_when_locate_then_none() -> None:
	# given
	no_reads = lambda o, n: b""  # noqa: E731
	# when / then
	assert locate_dng_preview(b"II*\x00\x08", 100, no_reads) is None
	assert locate_dng_preview(b"", 0, no_reads) is None


def test_given_not_a_tiff_when_locate_then_none() -> None:
	# given
	head = b"\xff\xd8\xff\xe0" + bytes(100)
	# when
	result = locate_dng_preview(head, len(head), lambda o, n: b"")
	# then
	assert result is None


def test_given_more_than_64_entries_when_locate_then_none() -> None:
	# given
	entries = {tag: ("H", [1]) for tag in range(0x0300, 0x0300 + 65)}
	dng = build_dng("<", [(8, entries)])
	# when / then
	assert _locate(dng) is None


def test_given_exactly_64_entries_when_locate_then_parsed() -> None:
	# given
	entries = jpeg_ifd(1280, 960, PREVIEW_AT, len(JPEG))
	entries.update({tag: ("H", [1]) for tag in range(0x0300, 0x0300 + 64 - len(entries))})
	dng = build_dng("<", [(8, entries)], jpeg_at=PREVIEW_AT)
	# when / then
	assert len(entries) == 64
	assert _locate(dng) is not None


def test_given_ifd0_pointing_at_itself_via_subifd_when_locate_then_none() -> None:
	# given
	entries = {0x0103: ("H", [1]), 0x014A: ("I", [8])}
	dng = build_dng("<", [(8, entries)])
	# when / then
	assert _locate(dng) is None


def test_given_subifd_listed_twice_when_locate_then_none() -> None:
	# given
	ifds = [(8, {0x014A: ("I", [1000, 1000])}), (1000, jpeg_ifd(1024, 683, PREVIEW_AT, len(JPEG)))]
	dng = build_dng("<", ifds, jpeg_at=PREVIEW_AT)
	# when / then
	assert _locate(dng) is None


def test_given_subifd_pointing_back_to_ifd0_when_locate_then_none() -> None:
	# given
	ifds = [(8, {0x014A: ("I", [1000, 8])}), (1000, {0x0103: ("H", [1])})]
	dng = build_dng("<", ifds)
	# when / then
	assert _locate(dng) is None


def test_given_more_than_8_subifds_when_locate_then_only_8_read() -> None:
	# given
	offsets = [1000 + 100 * index for index in range(12)]
	ifds = [(8, {0x014A: ("I", offsets)})] + [(offset, {0x0103: ("H", [1])}) for offset in offsets]
	dng = build_dng("<", ifds)
	# when
	location = _locate(dng)
	# then
	assert location is None
	assert [offset for offset, _ in dng.reads] == offsets[:DNG_MAX_SUBIFDS]


def test_given_ifd0_offset_beyond_file_when_locate_then_none_without_reads() -> None:
	# given
	dng = build_dng("<", [(8, jpeg_ifd(1, 1, 100, 10))], ifd0_pointer=10_000_000)
	# when / then
	assert _locate(dng) is None
	assert dng.reads == []


@pytest.mark.parametrize(
	("offset", "length"),
	[(PREVIEW_AT, 10_000_000), (10_000_000, 100), (PREVIEW_AT, 0), (2**32 - 1, 2**32 - 1)],
)
def test_given_preview_range_outside_file_when_locate_then_none(offset: int, length: int) -> None:
	# given
	entries = jpeg_ifd(1280, 960, offset, length)
	dng = build_dng("<", [(8, entries)], jpeg_at=PREVIEW_AT)
	# when / then
	assert _locate(dng) is None


def test_given_preview_larger_than_8_mb_when_locate_then_none() -> None:
	# given
	length = DNG_MAX_PREVIEW_BYTES + 1
	entries = jpeg_ifd(4032, 3024, PREVIEW_AT, length)
	dng = build_dng("<", [(8, entries)], size=PREVIEW_AT + length + 10)
	# when / then
	assert _locate(dng) is None


def test_given_preview_of_exactly_8_mb_when_locate_then_accepted() -> None:
	# given
	entries = jpeg_ifd(4032, 3024, PREVIEW_AT, DNG_MAX_PREVIEW_BYTES)
	dng = build_dng("<", [(8, entries)], size=PREVIEW_AT + DNG_MAX_PREVIEW_BYTES)
	# when / then
	assert _locate(dng) is not None


def test_given_read_at_raises_when_locate_then_error_propagates() -> None:
	# given
	entries = jpeg_ifd(1280, 960, PREVIEW_AT, len(JPEG))
	dng = build_dng("<", [(20_000, entries)], jpeg_at=PREVIEW_AT)

	def failing(offset: int, length: int) -> bytes:
		raise TimeoutError

	# when / then
	with pytest.raises(TimeoutError):
		locate_dng_preview(dng.head, dng.size, failing)


@pytest.mark.parametrize("order", ORDERS)
def test_given_random_mutations_of_valid_dngs_when_locate_then_never_raises_or_reads_outside_file(order: str) -> None:
	# given
	rng = random.Random(1234)  # noqa: S311 - seeded fuzzing, not crypto
	thumb = {0x0103: ("H", [1]), 0x014A: ("I", [900, 1500])}
	layouts = [
		build_dng(order, [(8, jpeg_ifd(1280, 960, PREVIEW_AT, len(JPEG), orientation=6))], jpeg_at=PREVIEW_AT),
		build_dng(order, [(7000, jpeg_ifd(1280, 960, PREVIEW_AT, len(JPEG)))], jpeg_at=PREVIEW_AT),
		build_dng(
			order,
			[(8, thumb), (900, jpeg_ifd(1024, 683, PREVIEW_AT, len(JPEG), subfile_type=1)), (1500, RAW_ENTRIES)],
			jpeg_at=PREVIEW_AT,
		),
	]
	for _ in range(300):
		base = rng.choice(layouts)
		data = bytearray(base.data)
		for _ in range(rng.randint(1, 12)):
			position = rng.randrange(0, min(len(data), 2200))
			data[position] = rng.randrange(256)
		size = rng.choice([len(data), len(data) + 500_000, rng.randrange(8, len(data) + 1)])
		mutated = DngFile(bytes(data[:size]), size)
		# when
		location = locate_dng_preview(mutated.head, mutated.size, mutated.read_at)
		# then
		assert all(0 <= offset and length > 0 and offset + length <= size for offset, length in mutated.reads)
		assert len(mutated.reads) <= 1 + DNG_MAX_SUBIFDS
		if location is not None:
			assert 0 < location.length <= DNG_MAX_PREVIEW_BYTES
			assert location.offset + location.length <= size
			assert 1 <= location.orientation <= 8


def test_given_random_bytes_when_locate_then_none_or_valid_without_raising() -> None:
	# given
	rng = random.Random(99)  # noqa: S311 - seeded fuzzing, not crypto
	for _ in range(200):
		header = rng.choice([b"II*\x00", b"MM\x00*"])
		body = bytes(rng.randrange(256) for _ in range(rng.randint(0, 300)))
		dng = DngFile(header + body, len(header + body) + rng.choice([0, 1000]))
		# when
		locate_dng_preview(dng.head, dng.size, dng.read_at)
		# then
		assert all(offset + length <= dng.size for offset, length in dng.reads)
