from __future__ import annotations

import asyncio
import contextlib
import secrets
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Protocol

from spacemaker.adapters.inbound.web.session import AppSession
from spacemaker.adapters.outbound.device.factory import device_repository_for
from spacemaker.adapters.outbound.filesystem.local import LocalFileSystem
from spacemaker.adapters.outbound.gallery.sqlite_index import SqliteGalleryIndex
from spacemaker.adapters.outbound.media.subprocess_converter import SubprocessMediaConverter
from spacemaker.adapters.outbound.media.subprocess_probe import SubprocessMediaProbe
from spacemaker.adapters.outbound.media.subprocess_thumbnails import SubprocessThumbnailGenerator
from spacemaker.adapters.outbound.media.tool_runner import ToolRunner
from spacemaker.adapters.outbound.tools.catalog_installer import CatalogToolInstaller
from spacemaker.application.convert_media import ConvertMedia
from spacemaker.application.delete_gallery_item import DeleteGalleryItem
from spacemaker.application.easy_session import should_auto_start_wifi_extract
from spacemaker.application.error_recovery import ErrorRecovery
from spacemaker.application.export_friendly_media import ExportFriendlyMedia
from spacemaker.application.extract_media import ExtractMedia
from spacemaker.application.file_share_manifest import (
	EMPTY_SHARE_FOLDER_MESSAGE,
	EmptyShareSelectionError,
	SharedManifestEntry,
	ShareDownloadTarget,
	build_share_manifest,
	count_shareable_files_in_root,
	dedupe_share_selection_paths,
	prune_share_selection_paths,
	write_folder_zip,
)
from spacemaker.application.generate_gallery import GenerateGallery
from spacemaker.application.get_gallery_item import GetGalleryItem
from spacemaker.application.library_image_issues import count_image_files_in_library_folder
from spacemaker.application.managed_tools import ManagedToolsService
from spacemaker.application.receive_uploaded_documents import ReceiveUploadedDocuments
from spacemaker.application.receive_uploaded_media import ReceiveUploadedMedia
from spacemaker.application.sync_gallery_index import SyncGalleryIndex
from spacemaker.application.transfer_usb_files import TransferUsbFiles
from spacemaker.application.wizard_state import wizard_actions
from spacemaker.bootstrap.app_meta import app_release_info
from spacemaker.bootstrap.bundled_tools import BundledTool, resolve_tool_path, tools_install_root
from spacemaker.bootstrap.paths import (
	default_documents_receive_root,
	default_library_root,
	display_user_path,
	normalize_library_root,
)
from spacemaker.bootstrap.ui_shell import UI_SHELL_VERSION
from spacemaker.domain.app_module import AppModule, LanSessionKind
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.convert_policy import (
	ConvertStartPolicy,
	convert_start_policy,
	should_auto_drain_after_upload,
	should_requeue_convert_drain,
)
from spacemaker.domain.extract_control import ExtractJobControl
from spacemaker.domain.gallery_export import ExportFormat, ExportJobPhase
from spacemaker.domain.gallery_export_job import GalleryExportJob
from spacemaker.domain.jobs import JobPhase, can_start_convert
from spacemaker.domain.library import JobProgress, LibraryFolder, TransferMode
from spacemaker.domain.source_folders import SourceFolder, parse_source_folders
from spacemaker.domain.transfer_folders import TransferFolder, parse_transfer_folders
from spacemaker.domain.ui_mode import UiMode
from spacemaker.domain.usb_file_transfer import (
	can_start_usb_file_transfer,
	default_transfer_folders,
	shows_iphone_limit_banner,
	transfer_control_flags,
)
from spacemaker.domain.video_encode import HardwareVideoEncoder


class WebSocketLike(Protocol):
	async def send_json(self, data: dict[str, object]) -> None: ...


def repo_root() -> Path:
	import sys

	from spacemaker.bootstrap.paths import bundle_resource_root

	bundled = bundle_resource_root()
	if bundled is not None:
		return bundled
	if getattr(sys, "frozen", False):
		meipass = getattr(sys, "_MEIPASS", None)
		if meipass:
			return Path(meipass)
	return Path(__file__).resolve().parents[3]


class AppServices:
	def __init__(self, *, port: int = 8765, bind_host: str = "0.0.0.0") -> None:
		self.port = port
		self.bind_host = bind_host
		self.session = AppSession(library_root=normalize_library_root(default_library_root()))
		self.filesystem = LocalFileSystem()
		self.managed_tools = ManagedToolsService(
			CatalogToolInstaller(repo_root=repo_root()),
			dest_dir=tools_install_root(),
		)
		self.runner = ToolRunner(path_fallback_allowed=self.managed_tools.permit_path_fallback)
		self.probe = SubprocessMediaProbe(self.runner)
		self.converter = SubprocessMediaConverter(self.runner)
		self.error_recovery = ErrorRecovery(self.filesystem)
		self.gallery_index = SqliteGalleryIndex()
		self.sync_gallery_index = SyncGalleryIndex(self.filesystem, self.probe, self.gallery_index)
		self.gallery = GenerateGallery(self.gallery_index)
		self.get_gallery_item = GetGalleryItem(self.filesystem, self.probe)
		self.delete_gallery_item = DeleteGalleryItem(self.filesystem)
		self.export_friendly = ExportFriendlyMedia(self.filesystem, self.converter, self.probe)
		self.thumbnails = SubprocessThumbnailGenerator(self.runner)
		self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="spacemaker-job")
		self._export_jobs: dict[str, GalleryExportJob] = {}
		self._export_lock = threading.Lock()
		self._ws_clients: set[WebSocketLike] = set()
		self._ws_lock = threading.Lock()
		self._event_loop: asyncio.AbstractEventLoop | None = None
		self._extract_control: ExtractJobControl | None = None
		self._wifi_upload_token: str = ""
		self._wifi_token_lock = threading.Lock()
		self._lan_session_kind: LanSessionKind = LanSessionKind.NONE
		self._receive_upload_token: str = ""
		self._share_session_token: str = ""
		self._wifi_uploads_in_flight = 0
		self._receive_uploads_in_flight = 0
		self._receive_control: ExtractJobControl | None = None
		self._share_entries: list[SharedManifestEntry] = []
		self._share_selection: list[str] = []
		self._extract_future: Future[None] | None = None
		self._usb_transfer_control: ExtractJobControl | None = None
		self._usb_transfer_future: Future[None] | None = None
		self._convert_control: ExtractJobControl | None = None
		self._convert_future: Future[None] | None = None
		self.receive_uploaded = ReceiveUploadedMedia(self.filesystem)
		self.receive_documents = ReceiveUploadedDocuments(self.filesystem)
		self._documents_receive_root = default_documents_receive_root()

	def devices_for(self, method: ConnectionMethod):
		if method is ConnectionMethod.WIFI:
			raise ValueError("Wi-Fi extract does not use DeviceRepository")
		return device_repository_for(method, runner=self.runner)

	def extract_use_case(self, method: ConnectionMethod) -> ExtractMedia:
		return ExtractMedia(self.devices_for(method), self.filesystem)

	def usb_transfer_use_case(self, method: ConnectionMethod) -> TransferUsbFiles:
		return TransferUsbFiles(self.devices_for(method), self.filesystem)

	def convert_use_case(self) -> ConvertMedia:
		return ConvertMedia(self.filesystem, self.converter, self.probe)

	def folder_counts(self, library_root: str) -> dict[str, int]:
		if not library_root:
			return {f.value: 0 for f in LibraryFolder}
		return {f.value: self.filesystem.count_files_in_folder(library_root, f) for f in LibraryFolder}

	def _documents_receive_file_count(self) -> int:
		root = Path(self._documents_receive_root)
		if not root.is_dir():
			return 0
		count = 0
		for path in root.rglob("*"):
			if path.is_file():
				count += 1
		return count

	def remove_gallery_item(self, library_root: str, relative_path: str) -> bool:
		removed = self.delete_gallery_item.run(library_root, relative_path)
		if removed:
			self.gallery_index.remove(library_root, relative_path)
			self.push_state()
		return removed

	def bind_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
		self._event_loop = loop

	def register_ws(self, ws: WebSocketLike) -> None:
		with self._ws_lock:
			self._ws_clients.add(ws)

	def unregister_ws(self, ws: WebSocketLike) -> None:
		with self._ws_lock:
			self._ws_clients.discard(ws)

	def broadcast(self, payload: dict[str, object]) -> None:
		loop = self._event_loop
		if loop is None:
			return
		with self._ws_lock:
			clients = list(self._ws_clients)
		for ws in clients:
			try:
				asyncio.run_coroutine_threadsafe(ws.send_json(payload), loop)
			except Exception:
				self.unregister_ws(ws)

	def reconcile_device_selection(self, connection_method: ConnectionMethod | None = None) -> bool:
		method = connection_method or self.session.connection_method
		if method is ConnectionMethod.WIFI:
			return False
		try:
			known = {d.device_id: d.label for d in self.devices_for(method).list_devices()}
		except FileNotFoundError:
			known = {}
		changed = False
		with self.session._lock:
			if method is not self.session.connection_method:
				return False
			if self.session.device_id and self.session.device_id not in known:
				self.session.device_id = ""
				self.session.device_label = ""
				changed = True
			elif self.session.device_id in known and self.session.device_label != known[self.session.device_id]:
				self.session.device_label = known[self.session.device_id]
				changed = True
		return changed

	def _missing_tools(self) -> list[str]:
		missing: list[str] = []
		for tool in BundledTool:
			try:
				resolve_tool_path(
					tool,
					allow_path_fallback=self.managed_tools.permit_path_fallback(tool),
				)
			except FileNotFoundError:
				missing.append(tool.value)
		return missing

	def _extract_job_active(self) -> bool:
		future = self._extract_future
		if future is not None and not future.done():
			return True
		with self.session._lock:
			if self.session.connection_method is ConnectionMethod.WIFI:
				return self.session.extract_phase in {JobPhase.RUNNING, JobPhase.PAUSED}
		return False

	def _extract_stopping(self) -> bool:
		control = self._extract_control
		future = self._extract_future
		if control is None or future is None or future.done():
			return False
		return control.was_stopped()

	def _convert_job_active(self) -> bool:
		future = self._convert_future
		return future is not None and not future.done()

	def shutdown(self, *, timeout_seconds: float = 10.0) -> None:
		self.stop_extract_and_wait(timeout_seconds=timeout_seconds)
		self.stop_usb_transfer_and_wait(timeout_seconds=timeout_seconds)
		self.stop_convert_and_wait(timeout_seconds=timeout_seconds)
		self._executor.shutdown(wait=False, cancel_futures=True)

	def enriched_snapshot(self) -> dict[str, object]:
		base = self.session.snapshot()
		with self.session._lock:
			folders = list(self.session.source_folders)
			has_folders = len(folders) > 0
			has_device = bool(self.session.device_id)
			extract_phase = self.session.extract_phase
			convert_phase = self.session.convert_phase
			convert_percent = self.session.convert_progress.percent
			library_root = self.session.library_root
		with self.session._lock:
			connection_method = self.session.connection_method
		actions = wizard_actions(
			extract_phase=extract_phase,
			convert_phase=convert_phase,
			convert_progress_percent=convert_percent,
			library_root=library_root,
			count_in_folder=self.filesystem.count_files_in_folder,
			has_device=has_device,
			has_source_folders=has_folders,
			connection_method=connection_method,
			convert_job_active=self._convert_job_active(),
		)
		base["extract_stopping"] = self._extract_stopping()
		base.update(actions)
		counts = self.folder_counts(library_root) if library_root else {f.value: 0 for f in LibraryFolder}
		base["library_counts"] = counts
		if library_root:
			base["image_import_issues"] = {
				"errors": count_image_files_in_library_folder(
					self.filesystem,
					library_root,
					LibraryFolder.ERROR,
				),
				"invalid": count_image_files_in_library_folder(
					self.filesystem,
					library_root,
					LibraryFolder.INVALID,
				),
			}
		else:
			base["image_import_issues"] = {"errors": 0, "invalid": 0}
		base["video_friendly_export_available"] = (
			self.converter.library_video_encoder() is not HardwareVideoEncoder.NONE
		)
		tools_status = self.managed_tools.status_dict()
		base["managed_tools"] = tools_status
		base["tools_ready"] = bool(tools_status.get("all_ready"))
		base["tools_downloads_pending"] = bool(tools_status.get("downloads_pending"))
		base["tools_setup_pending"] = bool(tools_status.get("setup_pending"))
		base["managed_tools_dir"] = tools_status.get("tools_dir", "")
		base["missing_tools"] = self._missing_tools()
		base["wifi_upload"] = self._wifi_upload_snapshot()
		base["receive_files_session"] = self._receive_files_snapshot()
		base["file_share"] = self._file_share_snapshot()
		base["documents_receive_root"] = self._documents_receive_root
		base["documents_receive_root_display"] = display_user_path(
			self._documents_receive_root,
			trailing_slash=True,
		)
		base["documents_receive_file_count"] = self._documents_receive_file_count()
		with self.session._lock:
			usb_phase = self.session.usb_transfer_phase
			usb_folders = list(self.session.transfer_folders)
			usb_has_device = bool(self.session.device_id)
			usb_method = self.session.connection_method
			usb_completed = self.session.usb_transfer_progress.completed
		usb_flags = transfer_control_flags(usb_phase)
		usb_flags["start"] = can_start_usb_file_transfer(
			has_device=usb_has_device,
			folders_selected=len(usb_folders) > 0,
			phase=usb_phase,
		)
		base["usb_transfer_actions"] = usb_flags
		base["usb_transfer_iphone_limit"] = shows_iphone_limit_banner(usb_method)
		base["usb_transfer_show_open_folder"] = (
			usb_phase in {JobPhase.DONE, JobPhase.STOPPED} and usb_completed > 0
		) or self._documents_receive_file_count() > 0
		if library_root:
			base["library_root_display"] = display_user_path(library_root, trailing_slash=True)
		else:
			base["library_root_display"] = display_user_path(default_library_root(), trailing_slash=True)
		base["share_selection"] = list(self._share_selection)
		base["ui_shell_version"] = UI_SHELL_VERSION
		base.update(app_release_info())
		return base

	def _wifi_upload_snapshot(self) -> dict[str, object]:
		from spacemaker.bootstrap.lan import lan_ip

		with self._wifi_token_lock:
			token = self._wifi_upload_token
		with self.session._lock:
			phase = self.session.extract_phase
			method = self.session.connection_method
		active = method is ConnectionMethod.WIFI and bool(token) and phase in {JobPhase.RUNNING, JobPhase.PAUSED}
		if not active:
			return {"active": False, "upload_url": "", "qr_url": ""}
		host = lan_ip()
		upload_url = f"http://{host}:{self.port}/upload?t={token}"
		return {
			"active": True,
			"upload_url": upload_url,
			"qr_url": f"/api/extract/upload-qr.svg?t={token}",
		}

	def _clear_wifi_token(self) -> None:
		with self._wifi_token_lock:
			self._wifi_upload_token = ""
			if self._lan_session_kind is LanSessionKind.PHOTO_UPLOAD:
				self._lan_session_kind = LanSessionKind.NONE

	def _mint_wifi_token(self) -> str:
		token = secrets.token_urlsafe(24)
		with self._wifi_token_lock:
			self._wifi_upload_token = token
			self._lan_session_kind = LanSessionKind.PHOTO_UPLOAD
		return token

	def _receive_files_snapshot(self) -> dict[str, object]:
		from spacemaker.bootstrap.lan import lan_ip

		with self._wifi_token_lock:
			token = self._receive_upload_token
			kind = self._lan_session_kind
		with self.session._lock:
			phase = self.session.receive_files_phase
		active = kind is LanSessionKind.RECEIVE_FILES and bool(token) and phase is JobPhase.RUNNING
		if not active:
			return {"active": False, "page_url": "", "qr_url": ""}
		host = lan_ip()
		page_url = f"http://{host}:{self.port}/receive?t={token}"
		return {
			"active": True,
			"page_url": page_url,
			"qr_url": f"/api/receive/qr.svg?t={token}",
		}

	def _file_share_snapshot(self) -> dict[str, object]:
		from spacemaker.bootstrap.lan import lan_ip

		with self._wifi_token_lock:
			token = self._share_session_token
			kind = self._lan_session_kind
		active = kind is LanSessionKind.SEND_FILES and bool(token) and bool(self._share_entries)
		if not active:
			return {"active": False, "page_url": "", "qr_url": "", "file_count": 0}
		host = lan_ip()
		page_url = f"http://{host}:{self.port}/share?t={token}"
		return {
			"active": True,
			"page_url": page_url,
			"qr_url": f"/api/share/qr.svg?t={token}",
			"file_count": len(self._share_entries),
		}

	def receive_token_valid(self, token: str) -> bool:
		if not token:
			return False
		with self._wifi_token_lock:
			return (
				self._lan_session_kind is LanSessionKind.RECEIVE_FILES
				and bool(self._receive_upload_token)
				and secrets.compare_digest(self._receive_upload_token, token)
			)

	def share_token_valid(self, token: str) -> bool:
		if not token:
			return False
		with self._wifi_token_lock:
			return (
				self._lan_session_kind is LanSessionKind.SEND_FILES
				and bool(self._share_session_token)
				and secrets.compare_digest(self._share_session_token, token)
			)

	def _clear_receive_session(self) -> None:
		with self._wifi_token_lock:
			self._receive_upload_token = ""
			if self._lan_session_kind is LanSessionKind.RECEIVE_FILES:
				self._lan_session_kind = LanSessionKind.NONE
		with self.session._lock:
			if self.session.receive_files_phase in {JobPhase.RUNNING, JobPhase.PAUSED}:
				self.session.receive_files_phase = JobPhase.STOPPED
		self._receive_control = None

	def _clear_share_session(self) -> None:
		with self._wifi_token_lock:
			self._share_session_token = ""
			if self._lan_session_kind is LanSessionKind.SEND_FILES:
				self._lan_session_kind = LanSessionKind.NONE

	def stop_active_lan_session(self) -> None:
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
		self._share_entries = []

	def enter_module(self, module: AppModule) -> None:
		self.stop_active_lan_session()
		if module is not AppModule.USB_FILE_TRANSFER:
			self.stop_usb_transfer_and_wait(timeout_seconds=30.0)
		with self.session._lock:
			self.session.active_module = module
			if module is AppModule.PHOTO_BACKUP:
				self.session.ui_mode = UiMode.EASY
				self.session.connection_method = ConnectionMethod.WIFI
				self.session.transfer_mode = TransferMode.COPY
			elif module is AppModule.USB_PHOTO_BACKUP:
				self.session.ui_mode = UiMode.ADVANCED
			elif module is AppModule.USB_FILE_TRANSFER:
				self.session.connection_method = ConnectionMethod.MTP
				self.session.transfer_mode = TransferMode.COPY
				self.session.transfer_folders = sorted(
					f.value for f in default_transfer_folders(ConnectionMethod.MTP)
				)
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
			self.reconcile_device_selection(ConnectionMethod.MTP)

	def leave_module_for_home(self) -> None:
		self.stop_active_lan_session()
		self.stop_usb_transfer_and_wait(timeout_seconds=30.0)
		self._share_selection = []
		with self.session._lock:
			self.session.active_module = AppModule.HOME

	def bootstrap_photo_backup(self) -> None:
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

	def start_receive_files_session(self) -> None:
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

	def _on_receive_paused(self) -> None:
		with self.session._lock:
			self.session.receive_files_phase = JobPhase.PAUSED
		self.push_state()

	def receive_session_accepts_uploads(self) -> bool:
		with self.session._lock:
			if self.session.receive_files_phase is not JobPhase.RUNNING:
				return False
		control = self._receive_control
		if control is None:
			return False
		return control.accepts_new_file()

	def record_receive_upload_progress(self) -> None:
		with self.session._lock:
			completed = self.session.receive_files_progress.completed + 1
			self.session.receive_files_progress = JobProgress(completed=completed, total=completed)
		self.push_state()

	def handle_receive_upload(self, token: str, raw_relative: str, temp_path: str, incoming_size: int) -> None:
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

	def set_share_selection(self, paths: list[str]) -> None:
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

	def resolve_share_download(self, token: str, entry_id: str) -> ShareDownloadTarget | None:
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

	def materialize_share_folder_zip(self, folder_root: Path) -> Path:
		import os
		import tempfile

		fd, name = tempfile.mkstemp(prefix="spacemaker-share-", suffix=".zip")
		os.close(fd)
		dest = Path(name)
		write_folder_zip(folder_root, dest)
		return dest

	def shared_file_for_download(self, token: str, entry_id: str) -> Path | None:
		target = self.resolve_share_download(token, entry_id)
		if target is None or target.kind != "file":
			return None
		return target.source_path

	def share_manifest(self, token: str) -> list[dict[str, str]]:
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

	def wifi_token_valid(self, token: str) -> bool:
		if not token:
			return False
		with self._wifi_token_lock:
			return bool(self._wifi_upload_token) and secrets.compare_digest(self._wifi_upload_token, token)

	def wifi_session_accepts_uploads(self) -> bool:
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

	def record_wifi_upload_progress(self) -> None:
		with self.session._lock:
			completed = self.session.extract_progress.completed + 1
			self.session.extract_progress = JobProgress(completed=completed, total=completed)
		self.push_state()

	def handle_wifi_upload(self, token: str, raw_relative: str, temp_path: str, incoming_size: int) -> None:
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

	def push_state(self) -> None:
		self.broadcast({"type": "state", "state": self.enriched_snapshot()})

	def push_gallery_export(self, job: GalleryExportJob) -> None:
		self.broadcast({"type": "gallery_export", "export": job.to_dict()})

	def get_export_job(self, job_id: str) -> GalleryExportJob | None:
		with self._export_lock:
			return self._export_jobs.get(job_id)

	def start_gallery_export(
		self, library_root: str, relative_path: str, export_format: ExportFormat
	) -> GalleryExportJob:
		job_id = uuid.uuid4().hex
		job = GalleryExportJob(
			job_id=job_id,
			relative_path=relative_path,
			export_format=export_format,
			phase=ExportJobPhase.RUNNING,
			percent=0,
			download_path="",
			error="",
			skipped_encode=False,
		)
		with self._export_lock:
			self._export_jobs[job_id] = job
		self.push_gallery_export(job)
		self._executor.submit(self._run_gallery_export, library_root, job_id, relative_path, export_format)
		return job

	def _run_gallery_export(
		self,
		library_root: str,
		job_id: str,
		relative_path: str,
		export_format: ExportFormat,
	) -> None:
		def on_progress(percent: int) -> None:
			with self._export_lock:
				job = self._export_jobs.get(job_id)
				if job is None:
					return
				job.percent = percent
				job.phase = ExportJobPhase.RUNNING
			self.push_gallery_export(self._export_jobs[job_id])

		try:
			result = self.export_friendly.run(
				library_root,
				relative_path,
				export_format,
				on_progress=on_progress,
			)
			with self._export_lock:
				job = self._export_jobs.get(job_id)
				if job is None:
					return
				job.phase = ExportJobPhase.DONE
				job.percent = 100
				job.download_path = result.download_path
				job.skipped_encode = result.skipped_encode
				job.error = ""
			self.push_gallery_export(self._export_jobs[job_id])
		except Exception as exc:
			with self._export_lock:
				job = self._export_jobs.get(job_id)
				if job is None:
					return
				job.phase = ExportJobPhase.ERROR
				job.error = str(exc)
			self.push_gallery_export(self._export_jobs[job_id])

	def start_extract(self) -> None:
		if self._extract_job_active():
			return
		with self.session._lock:
			if self.session.extract_phase in {JobPhase.RUNNING, JobPhase.PAUSED}:
				return
			method = self.session.connection_method
			if method is ConnectionMethod.WIFI:
				if not self.session.library_root:
					return
				self.session.transfer_mode = TransferMode.COPY
				self.session.extract_phase = JobPhase.RUNNING
				self.session.extract_progress = JobProgress(0, 0)
				self.session.last_error = ""
				library_root = self.session.library_root
				self.filesystem.ensure_library_folders(library_root)
			else:
				if not self.session.source_folders:
					return
				library_root = self.session.library_root
				device_id = self.session.device_id
				mode = self.session.transfer_mode
				folders = parse_source_folders(self.session.source_folders)
				self.session.extract_phase = JobPhase.RUNNING
				self.session.last_error = ""
		self._extract_control = ExtractJobControl(on_paused=self._on_extract_paused)
		if method is ConnectionMethod.WIFI:
			self._mint_wifi_token()
			self.push_state()
			return
		self.push_state()
		self._extract_future = self._executor.submit(
			self._run_extract,
			library_root,
			device_id,
			method,
			mode,
			folders,
		)

	def _on_extract_paused(self) -> None:
		with self.session._lock:
			self.session.extract_phase = JobPhase.PAUSED
		self.push_state()

	def pause_extract(self) -> None:
		with self.session._lock:
			is_wifi = self.session.connection_method is ConnectionMethod.WIFI
		if self._extract_control is not None:
			if is_wifi and self._wifi_uploads_in_flight == 0:
				self._extract_control.pause_immediately()
			else:
				self._extract_control.request_pause()

	def resume_extract(self) -> None:
		with self.session._lock:
			if self.session.extract_phase is not JobPhase.PAUSED:
				return
			self.session.extract_phase = JobPhase.RUNNING
		if self._extract_control is not None:
			self._extract_control.resume()
		self.push_state()

	def stop_extract(self) -> None:
		if self._extract_control is not None:
			self._extract_control.request_stop()
		was_wifi = False
		with self.session._lock:
			was_wifi = self.session.connection_method is ConnectionMethod.WIFI
			if was_wifi and self.session.extract_phase in {JobPhase.RUNNING, JobPhase.PAUSED}:
				self.session.extract_phase = JobPhase.STOPPED
		if was_wifi:
			self._clear_wifi_token()
		self.push_state()

	def stop_extract_and_wait(self, *, timeout_seconds: float = 300.0) -> None:
		future = self._extract_future
		with self.session._lock:
			phase_active = self.session.extract_phase in {JobPhase.RUNNING, JobPhase.PAUSED}
		if not phase_active and (future is None or future.done()):
			return
		self.stop_extract()
		deadline = time.monotonic() + timeout_seconds
		while self._wifi_uploads_in_flight > 0 and time.monotonic() < deadline:
			time.sleep(0.05)
		future = self._extract_future
		if future is not None:
			remaining = deadline - time.monotonic()
			if remaining > 0:
				with contextlib.suppress(Exception):
					future.result(timeout=remaining)

	def _usb_transfer_job_active(self) -> bool:
		future = self._usb_transfer_future
		return future is not None and not future.done()

	def start_usb_transfer(self) -> None:
		if self._usb_transfer_job_active():
			return
		with self.session._lock:
			if self.session.usb_transfer_phase in {JobPhase.RUNNING, JobPhase.PAUSED}:
				return
			if not self.session.transfer_folders or not self.session.device_id:
				return
			method = self.session.connection_method
			if method is ConnectionMethod.WIFI:
				return
			device_id = self.session.device_id
			mode = self.session.transfer_mode
			folders = parse_transfer_folders(self.session.transfer_folders)
			if not folders:
				return
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
		)

	def _on_usb_transfer_paused(self) -> None:
		with self.session._lock:
			self.session.usb_transfer_phase = JobPhase.PAUSED
		self.push_state()

	def pause_usb_transfer(self) -> None:
		if self._usb_transfer_control is not None:
			self._usb_transfer_control.request_pause()

	def resume_usb_transfer(self) -> None:
		with self.session._lock:
			if self.session.usb_transfer_phase is not JobPhase.PAUSED:
				return
			self.session.usb_transfer_phase = JobPhase.RUNNING
		if self._usb_transfer_control is not None:
			self._usb_transfer_control.resume()
		self.push_state()

	def stop_usb_transfer(self) -> None:
		if self._usb_transfer_control is not None:
			self._usb_transfer_control.request_stop()
		self.push_state()

	def stop_usb_transfer_and_wait(self, *, timeout_seconds: float = 300.0) -> None:
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
		self,
		dest_root: str,
		device_id: str,
		method: ConnectionMethod,
		mode: TransferMode,
		folders: frozenset[TransferFolder],
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

	def stop_convert(self) -> None:
		if self._convert_control is not None:
			self._convert_control.request_stop()
		self.push_state()

	def stop_convert_and_wait(self, *, timeout_seconds: float = 300.0) -> None:
		future = self._convert_future
		if future is None or future.done():
			return
		self.stop_convert()
		remaining = timeout_seconds
		with contextlib.suppress(Exception):
			future.result(timeout=remaining)

	def _run_extract(
		self,
		library_root: str,
		device_id: str,
		method: ConnectionMethod,
		mode: TransferMode,
		folders: frozenset[SourceFolder],
	) -> None:
		control = self._extract_control
		try:
			use_case = self.extract_use_case(method)

			def on_progress(progress: JobProgress) -> None:
				with self.session._lock:
					self.session.extract_progress = progress
				self.push_state()

			use_case.run(
				library_root,
				device_id,
				mode,
				source_folders=folders,
				control=control,
				on_progress=on_progress,
			)
			with self.session._lock:
				if control is not None and control.was_stopped():
					self.session.extract_phase = JobPhase.STOPPED
				elif control is not None and control.is_paused():
					self.session.extract_phase = JobPhase.PAUSED
				else:
					self.session.extract_phase = JobPhase.DONE
		except Exception as exc:
			with self.session._lock:
				self.session.extract_phase = JobPhase.ERROR
				self.session.last_error = str(exc)
		finally:
			self._extract_future = None
		self.push_state()

	def ensure_easy_session(self) -> None:
		with self.session._lock:
			self.session.active_module = AppModule.PHOTO_BACKUP
		self.bootstrap_photo_backup()

	def maybe_start_convert_drain(self) -> None:
		# Callers that ingest multiple files per request (e.g. the /api/upload
		# route) should call this once after the whole batch is saved, not per
		# file: starting the convert job before every file has landed in
		# originals/ makes its initial total (and displayed progress) reflect
		# only whatever was on disk at that instant, not the full batch.
		with self.session._lock:
			ui_mode = self.session.ui_mode
			convert_phase = self.session.convert_phase
			library_root = self.session.library_root
		if not library_root:
			return
		originals = self.filesystem.count_files_in_folder(library_root, LibraryFolder.ORIGINALS)
		if not should_auto_drain_after_upload(
			ui_mode=ui_mode,
			convert_phase=convert_phase,
			originals_count=originals,
		):
			return
		self.start_convert(policy=ConvertStartPolicy.CONCURRENT_WITH_EXTRACT)

	def start_convert(self, *, policy: ConvertStartPolicy | None = None) -> None:
		if self._convert_job_active():
			return
		with self.session._lock:
			library_root = self.session.library_root
			ui_mode = self.session.ui_mode
		if not library_root:
			return
		resolved = policy or convert_start_policy(ui_mode=ui_mode)
		if resolved is ConvertStartPolicy.STOP_EXTRACT_FIRST and self._extract_job_active():
			self.stop_extract_and_wait()
		with self.session._lock:
			originals = self.filesystem.count_files_in_folder(
				self.session.library_root,
				LibraryFolder.ORIGINALS,
			)
			if not can_start_convert(originals_count=originals, convert_job_active=False):
				return
			library_root = self.session.library_root
			self.session.convert_phase = JobPhase.RUNNING
			self.session.convert_progress = JobProgress(0, originals)
			self.session.last_error = ""
			concurrent = resolved is ConvertStartPolicy.CONCURRENT_WITH_EXTRACT
		self._convert_control = ExtractJobControl()
		self.push_state()
		self._convert_future = self._executor.submit(
			self._run_convert,
			library_root,
			concurrent_with_extract=concurrent,
		)

	def _run_convert(self, library_root: str, *, concurrent_with_extract: bool = False) -> None:
		control = self._convert_control
		self.sync_gallery_index.run(library_root)
		try:
			use_case = self.convert_use_case()
			cumulative_completed = 0

			while True:
				# Each use_case.run() call scans originals/ fresh and reports progress
				# starting from (0, <files in that scan>). Offset by everything already
				# completed in earlier drain passes so the UI shows one running total
				# (e.g. 0/2, 1/2, 2/2) instead of resetting to 0/1 per pass.
				base_completed = cumulative_completed

				def on_progress(progress: JobProgress, *, _base: int = base_completed) -> None:
					with self.session._lock:
						self.session.convert_progress = JobProgress(
							completed=_base + progress.completed,
							total=_base + progress.total,
						)
					self.push_state()

				batch_progress = use_case.run(library_root, control=control, on_progress=on_progress)
				cumulative_completed += batch_progress.completed
				with self.session._lock:
					remaining = self.filesystem.count_files_in_folder(library_root, LibraryFolder.ORIGINALS)
					extract_phase = self.session.extract_phase
				# Files uploaded while this same job was converting land in originals/
				# after use_case.run()'s own scan started, so drain them here in a loop
				# rather than recursing into start_convert(): that would re-enter while
				# self._convert_future (this job) is still not-done, so
				# _convert_job_active() would block it from actually starting anything.
				if not (
					(control is None or not control.was_stopped())
					and should_requeue_convert_drain(
						concurrent_with_extract=concurrent_with_extract,
						remaining_originals=remaining,
					)
				):
					break
				with self.session._lock:
					self.session.convert_progress = JobProgress(cumulative_completed, cumulative_completed + remaining)
				self.sync_gallery_index.run(library_root)
				self.push_state()
			progress = JobProgress(completed=cumulative_completed, total=cumulative_completed + remaining)
			with self.session._lock:
				if batch_progress.total == 0 and remaining > 0:
					self.session.convert_phase = JobPhase.ERROR
					self.session.last_error = (
						f"convert found no files under {library_root}/originals "
						f"({remaining} file(s) still on disk — check library path)"
					)
				elif (
					concurrent_with_extract and remaining == 0 and extract_phase in {JobPhase.RUNNING, JobPhase.PAUSED}
				):
					self.session.convert_phase = JobPhase.IDLE
					self.session.convert_progress = progress
					self.session.last_error = ""
				elif control is not None and control.was_stopped():
					self.session.convert_phase = JobPhase.STOPPED
					self.session.convert_progress = progress
					self.session.last_error = ""
				else:
					self.session.convert_phase = JobPhase.DONE
					self.session.convert_progress = progress
					error_count = self.filesystem.count_files_in_folder(library_root, LibraryFolder.ERROR)
					invalid_count = self.filesystem.count_files_in_folder(library_root, LibraryFolder.INVALID)
					if error_count or invalid_count:
						parts: list[str] = []
						if error_count:
							parts.append(f"{error_count} in error/")
						if invalid_count:
							parts.append(f"{invalid_count} in invalid/")
						hint = use_case.last_failure or "Check tools/ (magick, ffmpeg) and file formats."
						self.session.last_error = f"Convert finished with {', '.join(parts)}. Last failure: {hint}"
					else:
						self.session.last_error = ""
		except Exception as exc:
			with self.session._lock:
				self.session.convert_phase = JobPhase.ERROR
				self.session.last_error = str(exc)
		finally:
			self._convert_future = None
		self.sync_gallery_index.run(library_root)
		self.push_state()


def create_app(*, port: int = 8765, bind_host: str = "0.0.0.0"):
	from spacemaker.adapters.inbound.web.app import create_fastapi_app

	services = AppServices(port=port, bind_host=bind_host)
	return create_fastapi_app(services)
