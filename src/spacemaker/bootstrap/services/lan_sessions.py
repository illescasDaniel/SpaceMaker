from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
	from spacemaker.bootstrap.services.core import AppServices

import contextlib
import os
import secrets
import tempfile
import uuid
from pathlib import Path

from spacemaker.application.easy_session import should_auto_start_wifi_extract
from spacemaker.application.file_share_manifest import (
	EMPTY_SHARE_FOLDER_MESSAGE,
	EmptyShareSelectionError,
	ShareDownloadTarget,
	build_share_manifest,
	count_shareable_files_in_root,
	dedupe_share_selection_paths,
	prune_share_selection_paths,
	write_folder_zip,
)
from spacemaker.application.transfer_session import (
	EMPTY_TRANSFER_FOLDER_MESSAGE,
	EmptyTransferFolderError,
)
from spacemaker.bootstrap.paths import display_user_path
from spacemaker.domain.app_module import AppModule, LanSessionKind
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.extract_control import ExtractJobControl
from spacemaker.domain.jobs import JobPhase
from spacemaker.domain.library import JobProgress, TransferMode
from spacemaker.domain.transfer_session import TransferOrigin, TransferSessionItem
from spacemaker.domain.ui_mode import UiMode
from spacemaker.domain.usb_file_transfer import default_transfer_folders


class LanSessionMixin:
	def _clear_wifi_token(self: AppServices) -> None:
		with self._wifi_token_lock:
			self._wifi_upload_token = ""
			if self._lan_session_kind is LanSessionKind.PHOTO_UPLOAD:
				self._lan_session_kind = LanSessionKind.NONE

	def _mint_wifi_token(self: AppServices) -> str:
		token = secrets.token_urlsafe(24)
		with self._wifi_token_lock:
			self._wifi_upload_token = token
			self._lan_session_kind = LanSessionKind.PHOTO_UPLOAD
		return token

	def receive_token_valid(self: AppServices, token: str) -> bool:
		if not token:
			return False
		with self._wifi_token_lock:
			return (
				self._lan_session_kind is LanSessionKind.RECEIVE_FILES
				and bool(self._receive_upload_token)
				and secrets.compare_digest(self._receive_upload_token, token)
			)

	def share_token_valid(self: AppServices, token: str) -> bool:
		if not token:
			return False
		with self._wifi_token_lock:
			return (
				self._lan_session_kind is LanSessionKind.SEND_FILES
				and bool(self._share_session_token)
				and secrets.compare_digest(self._share_session_token, token)
			)

	def transfer_token_valid(self: AppServices, token: str) -> bool:
		if not token:
			return False
		with self._wifi_token_lock:
			return (
				self._lan_session_kind is LanSessionKind.TRANSFER_FILES
				and bool(self._transfer_session_token)
				and secrets.compare_digest(self._transfer_session_token, token)
			)

	def _clear_receive_session(self: AppServices) -> None:
		with self._wifi_token_lock:
			self._receive_upload_token = ""
			if self._lan_session_kind is LanSessionKind.RECEIVE_FILES:
				self._lan_session_kind = LanSessionKind.NONE
		with self.session._lock:
			if self.session.receive_files_phase in {JobPhase.RUNNING, JobPhase.PAUSED}:
				self.session.receive_files_phase = JobPhase.STOPPED
		self._receive_control = None

	def _clear_share_session(self: AppServices) -> None:
		with self._wifi_token_lock:
			self._share_session_token = ""
			if self._lan_session_kind is LanSessionKind.SEND_FILES:
				self._lan_session_kind = LanSessionKind.NONE

	def _wipe_transfer_staging(self: AppServices) -> None:
		import shutil

		root = self._transfer_staging_root
		self._transfer_staging_root = ""
		with self._transfer_lock:
			self._transfer_items = []
		if root and Path(root).is_dir():
			shutil.rmtree(root, ignore_errors=True)

	def _clear_transfer_session(self: AppServices) -> None:
		with self._wifi_token_lock:
			self._transfer_session_token = ""
			if self._lan_session_kind is LanSessionKind.TRANSFER_FILES:
				self._lan_session_kind = LanSessionKind.NONE
		self._wipe_transfer_staging()

	def stop_active_lan_session(self: AppServices) -> None:
		with self.session._lock:
			module = self.session.active_module
			extract_phase = self.session.extract_phase
			method = self.session.connection_method
		if module is AppModule.PHOTO_BACKUP and method is ConnectionMethod.WIFI:
			if extract_phase in {JobPhase.RUNNING, JobPhase.PAUSED}:
				self.stop_extract()
		elif extract_phase in {JobPhase.RUNNING, JobPhase.PAUSED} and method is ConnectionMethod.WIFI:
			self.stop_extract()
		self._clear_receive_session()
		self._clear_share_session()
		self._clear_transfer_session()
		self._share_entries = []

	def enter_module(self: AppServices, module: AppModule) -> None:
		self.stop_active_lan_session()
		if module is not AppModule.USB_FILE_TRANSFER:
			self.stop_usb_transfer_and_wait(timeout_seconds=30.0)
		self.release_device_mounts()
		with self.session._lock:
			self.session.active_module = module
			if module is AppModule.PHOTO_BACKUP:
				self.session.ui_mode = UiMode.EASY
				self.session.connection_method = ConnectionMethod.WIFI
				self.session.transfer_mode = TransferMode.COPY
			elif module is AppModule.USB_PHOTO_BACKUP:
				self.session.ui_mode = UiMode.ADVANCED
			elif module is AppModule.USB_FILE_TRANSFER:
				self.session.connection_method = ConnectionMethod.ADB
				self.session.transfer_mode = TransferMode.COPY
				self.session.transfer_folders = sorted(f.value for f in default_transfer_folders(ConnectionMethod.ADB))
				self.session.transfer_extra_paths = []
				self.session.device_id = ""
				self.session.device_label = ""
				self.session.usb_transfer_phase = JobPhase.IDLE
				self.session.usb_transfer_progress = JobProgress(0, 0)
				self.session.last_error = ""
		if module is AppModule.PHOTO_BACKUP:
			self.bootstrap_photo_backup()
		elif module is AppModule.RECEIVE_FILES:
			self.start_receive_files_session()
		elif module is AppModule.SEND_FILES:
			self._share_selection = []
			self._share_entries = []
			self._clear_share_session()
		elif module is AppModule.USB_FILE_TRANSFER:
			self.reconcile_device_selection(ConnectionMethod.ADB)
			with contextlib.suppress(Exception):
				cleanup = getattr(self.devices_for(ConnectionMethod.ADB), "cleanup_orphan_mounts", None)
				if callable(cleanup):
					cleanup()
		elif module is AppModule.TRANSFER_FILES:
			self.start_transfer_files_session()

	def leave_module_for_home(self: AppServices) -> None:
		self.stop_active_lan_session()
		self.stop_usb_transfer_and_wait(timeout_seconds=30.0)
		self.release_device_mounts()
		self._share_selection = []
		with self.session._lock:
			self.session.active_module = AppModule.HOME
			self.session.transfer_extra_paths = []

	def start_transfer_files_session(self: AppServices) -> None:

		self._wipe_transfer_staging()
		self._transfer_staging_root = tempfile.mkdtemp(prefix="spacemaker-transfer-")
		token = secrets.token_urlsafe(24)
		with self._wifi_token_lock:
			self._transfer_session_token = token
			self._lan_session_kind = LanSessionKind.TRANSFER_FILES
		self.push_state()

	def transfer_manifest(self: AppServices, token: str) -> list[dict[str, str]]:
		if not self.transfer_token_valid(token):
			return []
		with self._transfer_lock:
			items = list(self._transfer_items)
		return [self._transfer_item_row(item) for item in items]

	def resolve_transfer_download(self: AppServices, token: str, file_id: str) -> TransferSessionItem | None:
		if not self.transfer_token_valid(token) or not file_id:
			return None
		with self._transfer_lock:
			for item in self._transfer_items:
				if item.file_id == file_id and Path(item.staged_path).is_file():
					return item
		return None

	def save_transfer_item_to_documents(self: AppServices, file_id: str) -> dict[str, str]:
		"""Desktop Download: copy staged item into Documents/SpaceMaker (loopback)."""
		fid = (file_id or "").strip()
		if not fid:
			raise ValueError("file_id required")
		with self._wifi_token_lock:
			token = self._transfer_session_token
			active = self._lan_session_kind is LanSessionKind.TRANSFER_FILES and bool(token)
		if not active:
			raise PermissionError("transfer session ended")
		with self._transfer_lock:
			item = next((row for row in self._transfer_items if row.file_id == fid), None)
		if item is None or not Path(item.staged_path).is_file():
			raise FileNotFoundError("transfer item not found")
		Path(self._documents_receive_root).mkdir(parents=True, exist_ok=True)
		saved = self.save_transfer_to_documents.save(
			staged_path=item.staged_path,
			display_name=item.display_name,
			documents_root=self._documents_receive_root,
		)
		return {
			"saved_path": saved.saved_path,
			"saved_name": saved.saved_name,
			"saved_path_display": display_user_path(saved.saved_path),
		}

	def _next_transfer_file_id(self: AppServices) -> str:
		return f"t{uuid.uuid4().hex[:12]}"

	def handle_transfer_upload_file(
		self: AppServices,
		token: str,
		*,
		requested_name: str,
		temp_path: str,
		origin: TransferOrigin,
	) -> TransferSessionItem | None:
		if not self.transfer_token_valid(token):
			raise PermissionError("transfer session ended")
		staging = self._transfer_staging_root
		if not staging:
			raise PermissionError("transfer session ended")
		file_id = self._next_transfer_file_id()
		with self._transfer_lock:
			existing = list(self._transfer_items)
		outcome = self.stage_transfer.stage_file(
			staging,
			file_id=file_id,
			requested_name=requested_name,
			temp_path=temp_path,
			origin=origin,
			existing=existing,
		)
		if outcome.disposition.value == "added" and outcome.item is not None:
			with self._transfer_lock:
				self._transfer_items.append(outcome.item)
			self.push_state()
			return outcome.item
		self.push_state()
		return outcome.item

	def handle_transfer_upload_folder_files(
		self: AppServices,
		token: str,
		*,
		folder_name: str,
		relative_files: list[tuple[str, str]],
		origin: TransferOrigin,
	) -> TransferSessionItem | None:
		"""Stage a phone folder upload: relative_files is (relative_path, temp_path) pairs."""
		import shutil
		import tempfile

		from spacemaker.application.file_share_manifest import write_folder_zip
		from spacemaker.domain.transfer_session import TransferItemKind, folder_zip_display_name

		if not self.transfer_token_valid(token):
			raise PermissionError("transfer session ended")
		if not relative_files:
			raise EmptyTransferFolderError(EMPTY_TRANSFER_FOLDER_MESSAGE)
		staging = self._transfer_staging_root
		if not staging:
			raise PermissionError("transfer session ended")
		work = Path(tempfile.mkdtemp(prefix="spacemaker-transfer-folder-"))
		zip_temp: str | None = None
		try:
			for rel, temp_path in relative_files:
				dest = work / rel.replace("\\", "/")
				dest.parent.mkdir(parents=True, exist_ok=True)
				shutil.copy2(temp_path, dest)
				Path(temp_path).unlink(missing_ok=True)
			fd, zip_name = tempfile.mkstemp(prefix="spacemaker-transfer-", suffix=".zip")
			os.close(fd)
			zip_temp = zip_name
			write_folder_zip(work, Path(zip_temp))
			file_id = self._next_transfer_file_id()
			with self._transfer_lock:
				existing = list(self._transfer_items)
			outcome = self.stage_transfer.stage_file(
				staging,
				file_id=file_id,
				requested_name=folder_zip_display_name(folder_name),
				temp_path=zip_temp,
				origin=origin,
				existing=existing,
				kind=TransferItemKind.FOLDER_ZIP,
			)
			zip_temp = None
			if outcome.disposition.value == "added" and outcome.item is not None:
				with self._transfer_lock:
					self._transfer_items.append(outcome.item)
			self.push_state()
			return outcome.item
		finally:
			shutil.rmtree(work, ignore_errors=True)
			if zip_temp is not None:
				Path(zip_temp).unlink(missing_ok=True)

	def add_transfer_paths_from_desktop(self: AppServices, paths: list[str]) -> None:
		import tempfile

		if not self.transfer_token_valid(self._transfer_session_token):
			raise PermissionError("transfer session ended")
		staging = self._transfer_staging_root
		if not staging:
			raise PermissionError("transfer session ended")
		had_empty_folder = False
		for raw in paths:
			text = raw.strip()
			if not text:
				continue
			path = Path(text).expanduser().resolve()
			if path.is_dir():
				if count_shareable_files_in_root(path) == 0:
					had_empty_folder = True
					continue
				fd, zip_temp = tempfile.mkstemp(prefix="spacemaker-transfer-", suffix=".zip")
				os.close(fd)
				try:
					file_id = self._next_transfer_file_id()
					with self._transfer_lock:
						existing = list(self._transfer_items)
					outcome = self.stage_transfer.stage_folder_as_zip(
						staging,
						file_id=file_id,
						folder_path=str(path),
						origin=TransferOrigin.PC,
						existing=existing,
						zip_temp_path=zip_temp,
					)
					if outcome.disposition.value == "added" and outcome.item is not None:
						with self._transfer_lock:
							self._transfer_items.append(outcome.item)
				except EmptyTransferFolderError:
					had_empty_folder = True
					Path(zip_temp).unlink(missing_ok=True)
			elif path.is_file():
				fd, temp_name = tempfile.mkstemp(prefix="spacemaker-transfer-", suffix=path.suffix)
				os.close(fd)
				temp_path = Path(temp_name)
				try:
					temp_path.write_bytes(path.read_bytes())
					file_id = self._next_transfer_file_id()
					with self._transfer_lock:
						existing = list(self._transfer_items)
					outcome = self.stage_transfer.stage_file(
						staging,
						file_id=file_id,
						requested_name=path.name,
						temp_path=str(temp_path),
						origin=TransferOrigin.PC,
						existing=existing,
					)
					if outcome.disposition.value == "added" and outcome.item is not None:
						with self._transfer_lock:
							self._transfer_items.append(outcome.item)
				except Exception:
					temp_path.unlink(missing_ok=True)
					raise
		self.push_state()
		if had_empty_folder and not paths:
			raise EmptyTransferFolderError(EMPTY_TRANSFER_FOLDER_MESSAGE)
		if had_empty_folder and len(paths) == 1:
			raise EmptyTransferFolderError(EMPTY_TRANSFER_FOLDER_MESSAGE)

	def bootstrap_photo_backup(self: AppServices) -> None:
		with self.session._lock:
			self.session.ui_mode = UiMode.EASY
			self.session.connection_method = ConnectionMethod.WIFI
			self.session.transfer_mode = TransferMode.COPY
			extract_phase = self.session.extract_phase
			library_root = self.session.library_root
			active_module = self.session.active_module
		if library_root:
			self.filesystem.ensure_library_folders(library_root)
		if should_auto_start_wifi_extract(
			active_module=active_module,
			ui_mode=UiMode.EASY,
			extract_phase=extract_phase,
			library_root=library_root,
		):
			self.start_extract()
		self.maybe_start_convert_drain()

	def start_receive_files_session(self: AppServices) -> None:
		self.filesystem.ensure_parent_directory(str(Path(self._documents_receive_root) / "placeholder"))
		Path(self._documents_receive_root).mkdir(parents=True, exist_ok=True)
		self._receive_control = ExtractJobControl(on_paused=self._on_receive_paused)
		with self.session._lock:
			self.session.receive_files_phase = JobPhase.RUNNING
			self.session.receive_files_progress = JobProgress(0, 0)
		token = secrets.token_urlsafe(24)
		with self._wifi_token_lock:
			self._receive_upload_token = token
			self._lan_session_kind = LanSessionKind.RECEIVE_FILES
		self.push_state()

	def _on_receive_paused(self: AppServices) -> None:
		with self.session._lock:
			self.session.receive_files_phase = JobPhase.PAUSED
		self.push_state()

	def receive_session_accepts_uploads(self: AppServices) -> bool:
		with self.session._lock:
			if self.session.receive_files_phase is not JobPhase.RUNNING:
				return False
		control = self._receive_control
		if control is None:
			return False
		return control.accepts_new_file()

	def record_receive_upload_progress(self: AppServices) -> None:
		with self.session._lock:
			completed = self.session.receive_files_progress.completed + 1
			self.session.receive_files_progress = JobProgress(completed=completed, total=completed)
		self.push_state()

	def handle_receive_upload(
		self: AppServices, token: str, raw_relative: str, temp_path: str, incoming_size: int
	) -> None:
		if not self.receive_token_valid(token):
			raise PermissionError("receive session ended")
		control = self._receive_control
		if control is None or not control.accepts_new_file():
			raise PermissionError("receive session paused or stopped")
		self._receive_uploads_in_flight += 1
		try:
			outcome = self.receive_documents.ingest(
				self._documents_receive_root,
				raw_relative,
				temp_path=temp_path,
				incoming_size=incoming_size,
			)
		finally:
			self._receive_uploads_in_flight = max(0, self._receive_uploads_in_flight - 1)
			if control is not None:
				control.after_file()
		if outcome.disposition.value in {"saved", "skipped"}:
			self.record_receive_upload_progress()

	def set_share_selection(self: AppServices, paths: list[str]) -> None:
		raw = [p.strip() for p in paths if p and p.strip()]
		raw = dedupe_share_selection_paths(raw)
		clean, _had_empty_folder = prune_share_selection_paths(raw)
		entries = build_share_manifest(clean)
		if raw and not entries:
			raise EmptyShareSelectionError(EMPTY_SHARE_FOLDER_MESSAGE)
		if clean == self._share_selection and self._share_entries:
			return
		self._share_selection = clean
		self._share_entries = entries
		if not entries:
			self._clear_share_session()
			self.push_state()
			return
		with self._wifi_token_lock:
			if self._lan_session_kind is not LanSessionKind.SEND_FILES or not self._share_session_token:
				self._share_session_token = secrets.token_urlsafe(24)
				self._lan_session_kind = LanSessionKind.SEND_FILES
		self.push_state()

	def resolve_share_download(self: AppServices, token: str, entry_id: str) -> ShareDownloadTarget | None:
		if not self.share_token_valid(token):
			return None
		for entry in self._share_entries:
			if entry.entry_id != entry_id:
				continue
			path = Path(entry.absolute_path)
			if entry.kind == "file":
				if not path.is_file():
					return None
				return ShareDownloadTarget(
					kind="file",
					source_path=path,
					download_filename=path.name,
				)
			if entry.kind == "folder_zip":
				if not path.is_dir():
					return None
				if count_shareable_files_in_root(path) < 1:
					return None
				safe_name = entry.display_name.replace('"', "").strip() or "folder"
				return ShareDownloadTarget(
					kind="folder_zip",
					source_path=path,
					download_filename=f"{safe_name}.zip",
				)
		return None

	def materialize_share_folder_zip(self: AppServices, folder_root: Path) -> Path:
		import tempfile

		fd, name = tempfile.mkstemp(prefix="spacemaker-share-", suffix=".zip")
		os.close(fd)
		dest = Path(name)
		write_folder_zip(folder_root, dest)
		return dest

	def shared_file_for_download(self: AppServices, token: str, entry_id: str) -> Path | None:
		target = self.resolve_share_download(token, entry_id)
		if target is None or target.kind != "file":
			return None
		return target.source_path

	def share_manifest(self: AppServices, token: str) -> list[dict[str, str]]:
		if not self.share_token_valid(token):
			return []
		out: list[dict[str, str]] = []
		for entry in self._share_entries:
			row: dict[str, str] = {
				"id": entry.entry_id,
				"name": entry.display_name,
				"kind": entry.kind,
			}
			if entry.kind == "folder_zip":
				row["download_name"] = f"{entry.display_name}.zip"
			else:
				row["download_name"] = entry.display_name
			out.append(row)
		return out

	def wifi_token_valid(self: AppServices, token: str) -> bool:
		if not token:
			return False
		with self._wifi_token_lock:
			return bool(self._wifi_upload_token) and secrets.compare_digest(self._wifi_upload_token, token)

	def wifi_session_accepts_uploads(self: AppServices) -> bool:
		with self.session._lock:
			if self.session.connection_method is not ConnectionMethod.WIFI:
				return False
			if self.session.extract_phase not in {JobPhase.RUNNING, JobPhase.PAUSED}:
				return False
		control = self._extract_control
		if control is None:
			return False
		if self.session.extract_phase is JobPhase.PAUSED:
			return False
		return control.accepts_new_file()

	def record_wifi_upload_progress(self: AppServices) -> None:
		with self.session._lock:
			completed = self.session.extract_progress.completed + 1
			self.session.extract_progress = JobProgress(completed=completed, total=completed)
		self.push_state()

	def handle_wifi_upload(
		self: AppServices, token: str, raw_relative: str, temp_path: str, incoming_size: int
	) -> None:
		if not self.wifi_token_valid(token):
			raise PermissionError("upload session ended")
		control = self._extract_control
		if control is None or not control.accepts_new_file():
			raise PermissionError("upload session paused or stopped")
		with self.session._lock:
			library_root = self.session.library_root
		if not library_root:
			raise ValueError("library root not set")
		self._wifi_uploads_in_flight += 1
		try:
			outcome = self.receive_uploaded.ingest(
				library_root,
				raw_relative,
				temp_path=temp_path,
				incoming_size=incoming_size,
			)
		finally:
			self._wifi_uploads_in_flight = max(0, self._wifi_uploads_in_flight - 1)
			if control is not None:
				control.after_file()
		if outcome.disposition.value in {"saved", "skipped"}:
			self.record_wifi_upload_progress()
			self.maybe_start_convert_drain()
