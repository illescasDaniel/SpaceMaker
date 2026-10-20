from __future__ import annotations

import contextlib
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from spacemaker.domain.app_module import AppModule
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.device_browse import (
	BROWSE_PAGE_MAX,
	DeviceBrowseError,
	DeviceBrowseQuery,
	DeviceDirectoryScrollPage,
)
from spacemaker.domain.extract_control import ExtractJobControl
from spacemaker.domain.jobs import JobPhase
from spacemaker.domain.library import JobProgress, TransferMode
from spacemaker.domain.transfer_folders import (
	TransferFolder,
	existing_transfer_folders_from_dir_names,
	merge_extra_paths,
	parse_transfer_folders,
)


if TYPE_CHECKING:
	from spacemaker.bootstrap.services.core import AppServices


logger = logging.getLogger(__name__)


class UsbBrowseMixin:
	def _usb_transfer_job_active(self: AppServices) -> bool:
		future = self._usb_transfer_future
		return future is not None and not future.done()

	def is_busy(self: AppServices, method: ConnectionMethod, device_id: str) -> bool:
		"""``DeviceActivityPort``: a USB transfer or extract job is running on this connection method.

		Jobs are not tracked per device id, so ``device_id`` is unused for now.
		"""
		_ = device_id
		with self.session._lock:
			session_method = self.session.connection_method
		if session_method is not method:
			return False
		for future in (self._usb_transfer_future, self._extract_future):
			if future is not None and not future.done():
				return True
		return False

	def _usb_browse_snapshot(self: AppServices, method: ConnectionMethod, device_id: str) -> dict[str, object]:
		"""Picker availability plus preset exist-probe from ONE shallow listing of the storage root."""
		with self.session._lock:
			active = self.session.active_module
		# Only list from USB file transfer — never from other modules (a listing on every
		# wizard snapshot froze device selection once).
		if active is not AppModule.USB_FILE_TRANSFER:
			return {"picker_available": False, "available_folders": None, "hint": ""}
		if method is ConnectionMethod.WIFI or not device_id:
			return {
				"picker_available": False,
				"available_folders": None,
				"hint": "Add more needs a connected, authorized device.",
			}
		try:
			# Folder names only, so hidden entries are fine; the 500 cap matches the old probe.
			entries = (
				self.list_device_directory_use_case(method)
				.scroll(method.value, device_id, "", DeviceBrowseQuery(limit=BROWSE_PAGE_MAX, show_hidden=True))
				.entries
			)
		except DeviceBrowseError:
			return {"picker_available": True, "available_folders": None, "hint": ""}
		except Exception:
			logger.exception("preset exist-probe failed")
			return {"picker_available": True, "available_folders": None, "hint": ""}
		existing = existing_transfer_folders_from_dir_names(e.name for e in entries if e.is_dir)
		return {
			"picker_available": True,
			"available_folders": sorted(f.value for f in existing),
			"hint": "",
		}

	def list_device_directory(
		self: AppServices, method: ConnectionMethod, device_id: str, path: str, request: DeviceBrowseQuery
	) -> DeviceDirectoryScrollPage:
		return self.list_device_directory_use_case(method).scroll(method.value, device_id, path, request)

	def set_usb_transfer_extra_paths(self: AppServices, paths: list[str]) -> list[str]:
		merged = merge_extra_paths([], paths)
		with self.session._lock:
			self.session.transfer_extra_paths = merged
		return merged

	def set_extract_extra_paths(self: AppServices, paths: list[str]) -> list[str]:
		merged = merge_extra_paths([], paths)
		with self.session._lock:
			self.session.extract_extra_paths = merged
		return merged

	def clear_usb_transfer_extras(self: AppServices) -> None:
		with self.session._lock:
			self.session.transfer_extra_paths = []

	def start_usb_transfer(self: AppServices) -> None:
		if self._usb_transfer_job_active():
			return
		with self.session._lock:
			if self.session.usb_transfer_phase in {JobPhase.RUNNING, JobPhase.PAUSED}:
				return
			if not self.session.device_id:
				return
			folders = parse_transfer_folders(self.session.transfer_folders)
			extras = frozenset(self.session.transfer_extra_paths)
			if not folders and not extras:
				return
			method = self.session.connection_method
			if method is ConnectionMethod.WIFI:
				return
			device_id = self.session.device_id
			mode = self.session.transfer_mode
			self.session.usb_transfer_phase = JobPhase.RUNNING
			self.session.usb_transfer_progress = JobProgress(0, 0)
			self.session.last_error = ""
		dest_root = self.usb_transfer_destination()
		try:
			Path(dest_root).mkdir(parents=True, exist_ok=True)
			if not os.access(dest_root, os.W_OK | os.X_OK):
				raise PermissionError(f"{dest_root} is not writable")
		except OSError as exc:
			with self.session._lock:
				self.session.usb_transfer_phase = JobPhase.ERROR
				self.session.last_error = f"Cannot use destination folder: {exc}"
			self.push_state()
			return
		self._usb_transfer_control = ExtractJobControl(on_paused=self._on_usb_transfer_paused)
		self.push_state()
		self._usb_transfer_future = self._executor.submit(
			self._run_usb_transfer,
			dest_root,
			device_id,
			method,
			mode,
			folders,
			extras,
		)

	def _on_usb_transfer_paused(self: AppServices) -> None:
		with self.session._lock:
			self.session.usb_transfer_phase = JobPhase.PAUSED
		self.push_state()

	def pause_usb_transfer(self: AppServices) -> None:
		if self._usb_transfer_control is not None:
			self._usb_transfer_control.request_pause()

	def resume_usb_transfer(self: AppServices) -> None:
		with self.session._lock:
			if self.session.usb_transfer_phase is not JobPhase.PAUSED:
				return
			self.session.usb_transfer_phase = JobPhase.RUNNING
		if self._usb_transfer_control is not None:
			self._usb_transfer_control.resume()
		self.push_state()

	def stop_usb_transfer(self: AppServices) -> None:
		if self._usb_transfer_control is not None:
			self._usb_transfer_control.request_stop()
		self.push_state()

	def stop_usb_transfer_and_wait(self: AppServices, *, timeout_seconds: float = 300.0) -> None:
		future = self._usb_transfer_future
		with self.session._lock:
			phase_active = self.session.usb_transfer_phase in {JobPhase.RUNNING, JobPhase.PAUSED}
		if not phase_active and (future is None or future.done()):
			return
		self.stop_usb_transfer()
		future = self._usb_transfer_future
		if future is not None:
			with contextlib.suppress(Exception):
				future.result(timeout=timeout_seconds)

	def _run_usb_transfer(
		self: AppServices,
		dest_root: str,
		device_id: str,
		method: ConnectionMethod,
		mode: TransferMode,
		folders: frozenset[TransferFolder],
		extra_paths: frozenset[str],
	) -> None:
		control = self._usb_transfer_control
		try:
			use_case = self.usb_transfer_use_case(method)

			def on_progress(progress: JobProgress) -> None:
				with self.session._lock:
					self.session.usb_transfer_progress = progress
				self.push_state()

			use_case.run(
				dest_root,
				device_id,
				mode,
				folders=folders,
				extra_paths=extra_paths,
				control=control,
				on_progress=on_progress,
			)
			with self.session._lock:
				if control is not None and control.was_stopped():
					self.session.usb_transfer_phase = JobPhase.STOPPED
				elif control is not None and control.is_paused():
					self.session.usb_transfer_phase = JobPhase.PAUSED
				else:
					self.session.usb_transfer_phase = JobPhase.DONE
		except Exception as exc:
			logger.exception("USB transfer job crashed")
			with self.session._lock:
				self.session.usb_transfer_phase = JobPhase.ERROR
				self.session.last_error = str(exc)
		finally:
			self._usb_transfer_future = None
		self.push_state()
