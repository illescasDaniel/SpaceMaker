from __future__ import annotations

import threading
from dataclasses import dataclass, field

from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.jobs import JobPhase
from spacemaker.domain.library import JobProgress, TransferMode


@dataclass
class AppSession:
	library_root: str = ""
	connection_method: ConnectionMethod = ConnectionMethod.MTP
	transfer_mode: TransferMode = TransferMode.COPY
	device_id: str = ""
	device_label: str = ""
	source_folders: list[str] = field(default_factory=lambda: ["dcim", "pictures", "movies"])
	extract_phase: JobPhase = JobPhase.IDLE
	convert_phase: JobPhase = JobPhase.IDLE
	extract_progress: JobProgress = field(default_factory=lambda: JobProgress(0, 0))
	convert_progress: JobProgress = field(default_factory=lambda: JobProgress(0, 0))
	last_error: str = ""
	_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

	def snapshot(self) -> dict[str, object]:
		with self._lock:
			return {
				"library_root": self.library_root,
				"connection_method": self.connection_method.value,
				"transfer_mode": self.transfer_mode.value,
				"device_id": self.device_id,
				"device_label": self.device_label,
				"source_folders": list(self.source_folders),
				"extract": {
					"phase": self.extract_phase.value,
					"progress": {
						"completed": self.extract_progress.completed,
						"total": self.extract_progress.total,
						"percent": self.extract_progress.percent,
					},
				},
				"convert": {
					"phase": self.convert_phase.value,
					"progress": {
						"completed": self.convert_progress.completed,
						"total": self.convert_progress.total,
						"percent": self.convert_progress.percent,
					},
				},
				"last_error": self.last_error,
			}
