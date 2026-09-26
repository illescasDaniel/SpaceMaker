from __future__ import annotations

import threading
from dataclasses import dataclass, field

from spacemaker.domain.app_module import AppModule
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.jobs import JobPhase
from spacemaker.domain.library import JobProgress, TransferMode
from spacemaker.domain.transfer_folders import DEFAULT_ANDROID_TRANSFER_FOLDERS
from spacemaker.domain.ui_mode import UiMode


@dataclass
class AppSession:
	library_root: str = ""
	active_module: AppModule = AppModule.HOME
	ui_mode: UiMode = UiMode.EASY
	receive_files_phase: JobPhase = JobPhase.IDLE
	receive_files_progress: JobProgress = field(default_factory=lambda: JobProgress(0, 0))
	connection_method: ConnectionMethod = ConnectionMethod.WIFI
	transfer_mode: TransferMode = TransferMode.COPY
	device_id: str = ""
	device_label: str = ""
	source_folders: list[str] = field(default_factory=lambda: ["dcim", "pictures", "movies"])
	transfer_folders: list[str] = field(
		default_factory=lambda: sorted(f.value for f in DEFAULT_ANDROID_TRANSFER_FOLDERS),
	)
	extract_phase: JobPhase = JobPhase.IDLE
	convert_phase: JobPhase = JobPhase.IDLE
	usb_transfer_phase: JobPhase = JobPhase.IDLE
	extract_progress: JobProgress = field(default_factory=lambda: JobProgress(0, 0))
	convert_progress: JobProgress = field(default_factory=lambda: JobProgress(0, 0))
	usb_transfer_progress: JobProgress = field(default_factory=lambda: JobProgress(0, 0))
	last_error: str = ""
	_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

	def snapshot(self) -> dict[str, object]:
		with self._lock:
			return {
				"library_root": self.library_root,
				"active_module": self.active_module.value,
				"ui_mode": self.ui_mode.value,
				"receive_files": {
					"phase": self.receive_files_phase.value,
					"progress": {
						"completed": self.receive_files_progress.completed,
						"total": self.receive_files_progress.total,
						"percent": self.receive_files_progress.percent,
					},
				},
				"connection_method": self.connection_method.value,
				"transfer_mode": self.transfer_mode.value,
				"device_id": self.device_id,
				"device_label": self.device_label,
				"source_folders": list(self.source_folders),
				"transfer_folders": list(self.transfer_folders),
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
				"usb_transfer": {
					"phase": self.usb_transfer_phase.value,
					"progress": {
						"completed": self.usb_transfer_progress.completed,
						"total": self.usb_transfer_progress.total,
						"percent": self.usb_transfer_progress.percent,
					},
				},
				"last_error": self.last_error,
			}
