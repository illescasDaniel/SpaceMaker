from __future__ import annotations

from typing import Protocol

from spacemaker.domain.connection import ConnectionMethod


class DeviceActivityPort(Protocol):
	"""Whether a long-running job owns a device (a transfer always wins over previews).

	Implemented by the services object from its job state (``_usb_transfer_future`` / ``_extract_future``
	not done). Those jobs are not tracked per device id, so today it answers "any job on this
	``method`` is active"; refine to the device id if job state ever records it.
	"""

	def is_busy(self, method: ConnectionMethod, device_id: str) -> bool: ...
