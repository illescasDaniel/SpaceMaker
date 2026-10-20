from __future__ import annotations

from collections.abc import Callable

from spacemaker.application.device_stream_tokens import DeviceStreamTokens
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.device_browse import DeviceBrowseError
from spacemaker.domain.device_preview import (
	STREAM_READ_TIMEOUT_S,
	DevicePreviewError,
	DevicePreviewErrorKind,
	map_browse_error,
)
from spacemaker.domain.device_stream import (
	DeviceStreamChunk,
	DeviceStreamError,
	DeviceStreamErrorKind,
	parse_single_range,
)
from spacemaker.ports.outbound.device_activity import DeviceActivityPort
from spacemaker.ports.outbound.device_repository import DeviceRepositoryPort


class ReadDeviceStream:
	"""One byte range of a phone file, for the loopback stream endpoint that feeds the poster renderer.

	Strategy: resolve the token (``DeviceStreamError(UNKNOWN_TOKEN)``) -> ``DeviceActivityPort`` busy check
	(``DevicePreviewError(DEVICE_BUSY)``) -> ``parse_single_range`` against the grant's size -> one
	``read_range`` bounded by ``STREAM_READ_TIMEOUT_S`` (an empty read, i.e. the file shrank, is
	``RANGE_NOT_SATISFIABLE`` with the granted size). Device failures (``DeviceBrowseError``) are mapped to
	``DevicePreviewError`` exactly like ``GetDevicePreview`` does.
	"""

	def __init__(
		self,
		tokens: DeviceStreamTokens,
		resolve_repository: Callable[[ConnectionMethod], DeviceRepositoryPort],
		activity: DeviceActivityPort,
	) -> None:
		self._tokens = tokens
		self._resolve_repository = resolve_repository
		self._activity = activity

	def __call__(self, token: str, range_header: str | None) -> DeviceStreamChunk:
		grant = self._tokens.resolve(token)
		if grant is None:
			raise DeviceStreamError(DeviceStreamErrorKind.UNKNOWN_TOKEN)
		if self._activity.is_busy(grant.method, grant.device_id):
			raise DevicePreviewError(DevicePreviewErrorKind.DEVICE_BUSY)
		byte_range = parse_single_range(range_header, grant.size)
		repository = self._resolve_repository(grant.method)
		try:
			data = repository.read_range(
				grant.device_id, grant.path, byte_range.start, byte_range.length, STREAM_READ_TIMEOUT_S
			)
		except DeviceBrowseError as exc:
			raise map_browse_error(exc) from exc
		if not data:  # the file shrank since the token was minted: the granted size is stale
			raise DeviceStreamError(DeviceStreamErrorKind.RANGE_NOT_SATISFIABLE, str(grant.size))
		return DeviceStreamChunk(data, byte_range.start, byte_range.start + len(data) - 1, grant.size)
