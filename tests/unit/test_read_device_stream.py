# Video posters, ReadDeviceStream (SPEC "Video posters — API" stream table and trust boundary):
#   unknown/revoked token -> UNKNOWN_TOKEN; busy device -> DEVICE_BUSY; range read through read_range with
#   STREAM_READ_TIMEOUT_S on the grant's path only; chunk start/end/total; <= 4 MiB; Range errors from
#   parse_single_range; device failures mapped to DevicePreviewError (unplugged/timeout/unauthorized -> 503 kinds).
import pytest
from tests.unit.fakes import FakeDeviceActivity, FakeDeviceRepository

from spacemaker.application.device_stream_tokens import DeviceStreamTokens
from spacemaker.application.read_device_stream import ReadDeviceStream
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.device_browse import DeviceBrowseErrorKind
from spacemaker.domain.device_preview import (
	STREAM_MAX_CHUNK_BYTES,
	STREAM_READ_TIMEOUT_S,
	DevicePreviewError,
	DevicePreviewErrorKind,
)
from spacemaker.domain.device_stream import (
	DeviceStreamChunk,
	DeviceStreamError,
	DeviceStreamErrorKind,
	DeviceStreamGrant,
)


PATH = "DCIM/Camera/clip.mp4"
CONTENT = bytes(range(256)) * 4  # 1024 bytes


class _Rig:
	def __init__(self) -> None:
		self.devices = FakeDeviceRepository()
		self.devices.range_data[PATH] = CONTENT
		self.activity = FakeDeviceActivity()
		self.tokens = DeviceStreamTokens()
		self.resolved: list[ConnectionMethod] = []
		self.use_case = ReadDeviceStream(self.tokens, self._resolve, self.activity)

	def _resolve(self, method: ConnectionMethod) -> FakeDeviceRepository:
		self.resolved.append(method)
		return self.devices

	def mint(self, path: str = PATH, size: int = len(CONTENT), method: ConnectionMethod = ConnectionMethod.ADB) -> str:
		return self.tokens.mint(DeviceStreamGrant(method, "dev1", path, size))


def _rig() -> _Rig:
	return _Rig()


def test_given_valid_token_and_range_when_read_then_chunk_with_start_end_total() -> None:
	# given
	rig = _rig()
	token = rig.mint()
	# when
	chunk = rig.use_case(token, "bytes=100-199")
	# then
	assert chunk == DeviceStreamChunk(CONTENT[100:200], 100, 199, len(CONTENT))


def test_given_valid_token_when_read_then_one_range_read_on_grant_path_with_timeout() -> None:
	# given
	rig = _rig()
	token = rig.mint()
	# when
	rig.use_case(token, "bytes=10-19")
	# then
	assert rig.devices.read_range_calls == [("dev1", PATH, 10, 10, STREAM_READ_TIMEOUT_S)]
	assert rig.resolved == [ConnectionMethod.ADB]
	assert rig.activity.calls == [(ConnectionMethod.ADB, "dev1")]


def test_given_afc_grant_when_read_then_afc_repository_resolved() -> None:
	# given
	rig = _rig()
	token = rig.mint(method=ConnectionMethod.AFC)
	# when
	rig.use_case(token, "bytes=0-9")
	# then
	assert rig.resolved == [ConnectionMethod.AFC]


def test_given_open_ended_range_when_read_then_requests_cap_bounded_by_size() -> None:
	# given
	rig = _rig()
	token = rig.mint()
	# when
	chunk = rig.use_case(token, "bytes=1000-")
	# then
	assert chunk == DeviceStreamChunk(CONTENT[1000:], 1000, 1023, len(CONTENT))
	assert rig.devices.read_range_calls[0][2:4] == (1000, 24)


def test_given_huge_file_when_open_ended_range_then_never_asks_more_than_4_mib() -> None:
	# given
	rig = _rig()
	token = rig.mint(size=500 * 1024 * 1024)
	# when
	rig.use_case(token, "bytes=0-")
	# then
	assert rig.devices.read_range_calls[0][3] == STREAM_MAX_CHUNK_BYTES == 4 * 1024 * 1024


def test_given_unknown_token_when_read_then_unknown_token_without_device_calls() -> None:
	# given
	rig = _rig()
	# when / then
	with pytest.raises(DeviceStreamError) as raised:
		rig.use_case("not-a-token", "bytes=0-9")
	assert raised.value.kind is DeviceStreamErrorKind.UNKNOWN_TOKEN
	assert rig.devices.device_calls == 0
	assert rig.activity.calls == []


def test_given_revoked_token_when_read_then_unknown_token() -> None:
	# given
	rig = _rig()
	token = rig.mint()
	rig.tokens.revoke(token)
	# when / then
	with pytest.raises(DeviceStreamError) as raised:
		rig.use_case(token, "bytes=0-9")
	assert raised.value.kind is DeviceStreamErrorKind.UNKNOWN_TOKEN
	assert rig.devices.device_calls == 0


def test_given_busy_device_when_read_then_device_busy_without_read() -> None:
	# given
	rig = _rig()
	token = rig.mint()
	rig.activity.busy = True
	# when / then
	with pytest.raises(DevicePreviewError) as raised:
		rig.use_case(token, "bytes=0-9")
	assert raised.value.kind is DevicePreviewErrorKind.DEVICE_BUSY
	assert rig.devices.device_calls == 0


@pytest.mark.parametrize("header", [None, "bytes=-10", "bytes=0-1,4-5", "garbage"])
def test_given_missing_or_malformed_range_when_read_then_range_required_without_read(header: str | None) -> None:
	# given
	rig = _rig()
	token = rig.mint()
	# when / then
	with pytest.raises(DeviceStreamError) as raised:
		rig.use_case(token, header)
	assert raised.value.kind is DeviceStreamErrorKind.RANGE_REQUIRED
	assert rig.devices.device_calls == 0


def test_given_start_past_size_when_read_then_not_satisfiable_with_size_and_no_read() -> None:
	# given
	rig = _rig()
	token = rig.mint()
	# when / then
	with pytest.raises(DeviceStreamError) as raised:
		rig.use_case(token, f"bytes={len(CONTENT)}-")
	assert raised.value.kind is DeviceStreamErrorKind.RANGE_NOT_SATISFIABLE
	assert raised.value.detail == str(len(CONTENT))
	assert rig.devices.device_calls == 0


def test_given_token_bound_to_one_file_when_read_then_only_that_path_is_read() -> None:
	# given
	rig = _rig()
	rig.devices.range_data["Private/secret.mp4"] = b"secret" * 100
	token = rig.mint()
	# when
	rig.use_case(token, "bytes=0-9")
	rig.use_case(token, "bytes=20-29")
	# then
	assert {call[1] for call in rig.devices.read_range_calls} == {PATH}


def test_given_two_tokens_when_read_then_each_reads_its_own_file() -> None:
	# given
	rig = _rig()
	rig.devices.range_data["b.mp4"] = b"B" * 50
	first = rig.mint()
	second = rig.mint("b.mp4", size=50)
	# when
	chunk_b = rig.use_case(second, "bytes=0-4")
	chunk_a = rig.use_case(first, "bytes=0-4")
	# then
	assert chunk_b.data == b"BBBBB"
	assert chunk_a.data == CONTENT[:5]


@pytest.mark.parametrize(
	("failure", "expected"),
	[
		(DeviceBrowseErrorKind.UNPLUGGED, DevicePreviewErrorKind.UNPLUGGED),
		(DeviceBrowseErrorKind.UNAUTHORIZED, DevicePreviewErrorKind.UNAUTHORIZED),
		(DeviceBrowseErrorKind.TIMEOUT, DevicePreviewErrorKind.TIMEOUT),
		(DeviceBrowseErrorKind.NOT_FOUND, DevicePreviewErrorKind.NO_PREVIEW),
	],
)
def test_given_device_read_fails_when_read_then_browse_error_mapped(
	failure: DeviceBrowseErrorKind, expected: DevicePreviewErrorKind
) -> None:
	# given
	rig = _rig()
	token = rig.mint()
	rig.devices.range_errors[PATH] = failure
	# when / then
	with pytest.raises(DevicePreviewError) as raised:
		rig.use_case(token, "bytes=0-9")
	assert raised.value.kind is expected


def test_given_file_shrank_when_read_then_not_satisfiable_with_granted_size() -> None:
	# given
	rig = _rig()
	rig.devices.range_data[PATH] = b""
	token = rig.mint()
	# when
	with pytest.raises(DeviceStreamError) as raised:
		rig.use_case(token, "bytes=0-99")
	# then
	assert raised.value.kind is DeviceStreamErrorKind.RANGE_NOT_SATISFIABLE
	assert raised.value.detail == str(len(CONTENT))
