from spacemaker.adapters.outbound.tools.compression_capability import ManagedCompressionTools
from spacemaker.domain.managed_tool import ManagedToolStatus, ToolInstallPhase, ToolResolution


class _FakeManagedTools:
	def __init__(self, items: list[ManagedToolStatus]) -> None:
		self._items = items

	def snapshot(self) -> list[ManagedToolStatus]:
		return list(self._items)


def test_given_magick_and_ffmpeg_ready_when_available_then_true():
	# given
	tools = ManagedCompressionTools(
		_FakeManagedTools(
			[
				ManagedToolStatus("magick", ToolInstallPhase.READY, ToolResolution.MANAGED, "/m"),
				ManagedToolStatus("ffmpeg", ToolInstallPhase.READY, ToolResolution.PATH, "/f"),
			]
		)
	)

	# when / then
	assert tools.available()


def test_given_magick_missing_when_available_then_false():
	# given
	tools = ManagedCompressionTools(
		_FakeManagedTools(
			[
				ManagedToolStatus("magick", ToolInstallPhase.FAILED, ToolResolution.MISSING),
				ManagedToolStatus("ffmpeg", ToolInstallPhase.READY, ToolResolution.MANAGED, "/f"),
			]
		)
	)

	# when / then
	assert not tools.available()
