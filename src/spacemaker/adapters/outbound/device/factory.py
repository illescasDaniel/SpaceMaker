from __future__ import annotations

from spacemaker.adapters.outbound.device.adb_repository import AdbDeviceRepository
from spacemaker.adapters.outbound.device.mtp_repository import MtpDeviceRepository
from spacemaker.adapters.outbound.media.tool_runner import ToolRunner
from spacemaker.bootstrap.bundled_tools import BundledTool
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.ports.outbound.device_repository import DeviceRepositoryPort


def device_repository_for(
	method: ConnectionMethod,
	*,
	runner: ToolRunner | None = None,
) -> DeviceRepositoryPort:
	run = runner or ToolRunner()
	if method is ConnectionMethod.ADB:
		adb_path = run.path(BundledTool.ADB)
		return AdbDeviceRepository(adb_path)
	return MtpDeviceRepository(run)
