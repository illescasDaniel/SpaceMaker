from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
	from spacemaker.bootstrap.services.core import AppServices

import contextlib
from pathlib import Path

from spacemaker.application.usb_transfer_browse import (
	device_relative_paths_from_host_picks,
	probe_existing_transfer_folders,
)
from spacemaker.domain.app_module import AppModule
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.extract_control import ExtractJobControl
from spacemaker.domain.jobs import JobPhase
from spacemaker.domain.library import JobProgress, TransferMode
from spacemaker.domain.transfer_folders import TransferFolder, merge_extra_paths, parse_transfer_folders


class UsbBrowseMixin:
	def _usb_transfer_job_active(self: AppServices) -> bool:
		future = self._usb_transfer_future
		return future is not None and not future.done()

	def _usb_browse_snapshot(self: AppServices, method: ConnectionMethod, device_id: str) -> dict[str, object]:
		with self.session._lock:
			active = self.session.active_module
		# Never mount FUSE from photo-backup / other modules — that froze ADB device
		# selection on the wizard when enriched_snapshot ran after auto-select.
		if active is not AppModule.USB_FILE_TRANSFER:
			return {
				"mount_available": False,
				"mount_root": "",
				"available_folders": None,
				"hint": "",
			}
		if method is ConnectionMethod.WIFI or not device_id:
			return {
				"mount_available": False,
				"mount_root": "",
				"available_folders": None,
				"hint": "Connect a device to browse phone folders.",
			}
		try:
			repo = self.devices_for(method)
		except Exception:
			repo = None
		if method is ConnectionMethod.ADB and repo is not None:
			return self._adb_browse_snapshot(repo, device_id)
		# AFC (and any other mount-backed method): mount when needed for exist-probe.
		try:
			mount = repo.browse_root(device_id) if repo is not None else None
		except Exception:
			mount = None
			repo = None
		if mount:
			existing = probe_existing_transfer_folders(mount)
			return {
				"mount_available": True,
				"mount_root": mount,
				"available_folders": sorted(f.value for f in existing),
				"hint": "",
			}
		if method is ConnectionMethod.AFC:
			hint = "Add files/folder needs an ifuse mount for iPhone USB. Desktop app only."
		else:
			hint = "Add files/folder needs a mounted phone. Desktop app only."
		return {
			"mount_available": False,
			"mount_root": "",
			"available_folders": None,
			"hint": hint,
		}

	def _adb_browse_snapshot(self: AppServices, repo: object, device_id: str) -> dict[str, object]:
		"""ADB presets via shell; FUSE only if already mounted (Add mounts lazily)."""
		available: list[str] | None = None
		probe = getattr(repo, "probe_existing_transfer_folders", None)
		if callable(probe):
			try:
				existing = probe(device_id)
				available = sorted(f.value for f in existing)
			except Exception:
				available = None
		backend = getattr(repo, "browse_backend_available", None)
		backend_ok = bool(backend()) if callable(backend) else False
		peek = getattr(repo, "peek_browse_root", None)
		mount = peek(device_id) if callable(peek) else None
		if mount:
			# Prefer shallow mount names when a live mount already exists.
			with contextlib.suppress(Exception):
				from_mount = probe_existing_transfer_folders(mount)
				available = sorted(f.value for f in from_mount)
			return {
				"mount_available": True,
				"mount_root": mount,
				"available_folders": available,
				"hint": "",
			}
		if backend_ok:
			return {
				"mount_available": True,
				"mount_root": "",
				"available_folders": available,
				"hint": "",
			}
		hint = (
			"Add files/folder needs adbfs on PATH (e.g. AUR adbfs-rootless-git). "
			"Preset folders can still appear via ADB. Desktop app only."
		)
		return {
			"mount_available": False,
			"mount_root": "",
			"available_folders": available,
			"hint": hint,
		}

	def ensure_usb_browse_mount(self: AppServices) -> str:
		"""Mount the phone for Add files/folder (lazy). Raises ValueError on failure."""
		with self.session._lock:
			method = self.session.connection_method
			device_id = self.session.device_id
			active = self.session.active_module
		if active is not AppModule.USB_FILE_TRANSFER:
			raise ValueError("Add files/folder is only available in USB file transfer")
		if method is ConnectionMethod.WIFI or not device_id:
			raise ValueError("select a USB device first")
		repo = self.devices_for(method)
		cleanup = getattr(repo, "cleanup_orphan_mounts", None)
		if callable(cleanup):
			with contextlib.suppress(Exception):
				cleanup()
		mount = repo.browse_root(device_id)
		if not mount:
			if method is ConnectionMethod.ADB:
				raise ValueError("Could not mount with adbfs. Install adbfs-rootless-git (or similar) and retry.")
			raise ValueError("phone mount not available for Add files/folder")
		return mount

	def add_usb_transfer_extras_from_host(self: AppServices, host_paths: list[str]) -> list[str]:
		with self.session._lock:
			method = self.session.connection_method
			device_id = self.session.device_id
			existing = list(self.session.transfer_extra_paths)
		if method is ConnectionMethod.WIFI or not device_id:
			raise ValueError("select a USB device first")
		mount = self.ensure_usb_browse_mount()
		accepted = device_relative_paths_from_host_picks(mount, host_paths)
		if not accepted:
			raise ValueError("selected paths must be under the phone mount")
		merged = merge_extra_paths(existing, accepted)
		with self.session._lock:
			self.session.transfer_extra_paths = merged
		return merged

	def set_usb_transfer_extra_paths(self: AppServices, paths: list[str]) -> list[str]:
		merged = merge_extra_paths([], paths)
		with self.session._lock:
			self.session.transfer_extra_paths = merged
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
		dest_root = self._documents_receive_root
		Path(dest_root).mkdir(parents=True, exist_ok=True)
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
			with self.session._lock:
				self.session.usb_transfer_phase = JobPhase.ERROR
				self.session.last_error = str(exc)
		finally:
			self._usb_transfer_future = None
		self.push_state()
