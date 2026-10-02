from __future__ import annotations

import asyncio
import contextlib
import threading
from collections.abc import Coroutine
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypeVar

from spacemaker.adapters.inbound.web.session import AppSession
from spacemaker.adapters.outbound.device.factory import device_repository_for
from spacemaker.adapters.outbound.filesystem.local import LocalFileSystem
from spacemaker.adapters.outbound.filesystem.sha256_hasher import Sha256ContentHasher
from spacemaker.adapters.outbound.gallery.sqlite_index import SqliteGalleryIndex
from spacemaker.adapters.outbound.media.subprocess_converter import SubprocessMediaConverter
from spacemaker.adapters.outbound.media.subprocess_probe import SubprocessMediaProbe
from spacemaker.adapters.outbound.media.subprocess_thumbnails import SubprocessThumbnailGenerator
from spacemaker.adapters.outbound.media.tool_runner import ToolRunner
from spacemaker.adapters.outbound.preferences.json_store import JsonUserPreferences
from spacemaker.adapters.outbound.preferences.passcode_store import JsonPasscodeStore
from spacemaker.adapters.outbound.security.monotonic_clock import MonotonicClock
from spacemaker.adapters.outbound.security.scrypt_crypto import ScryptPasscodeCrypto
from spacemaker.adapters.outbound.tools.catalog_installer import CatalogToolInstaller
from spacemaker.adapters.outbound.tools.compression_capability import ManagedCompressionTools
from spacemaker.application.clear_browser_cache import ClearBrowserCache
from spacemaker.application.clear_user_preferences import ClearUserPreferences
from spacemaker.application.convert_media import ConvertMedia
from spacemaker.application.delete_gallery_item import DeleteGalleryItem
from spacemaker.application.error_recovery import ErrorRecovery
from spacemaker.application.export_friendly_media import ExportFriendlyMedia
from spacemaker.application.extract_media import ExtractMedia
from spacemaker.application.file_share_manifest import (
	SharedManifestEntry,
)
from spacemaker.application.generate_gallery import GenerateGallery
from spacemaker.application.get_gallery_item import GetGalleryItem
from spacemaker.application.network_passcode import NetworkPasscode
from spacemaker.application.promote_originals import PromoteOriginalsToProcessed
from spacemaker.application.receive_uploaded_documents import ReceiveUploadedDocuments
from spacemaker.application.receive_uploaded_media import ReceiveUploadedMedia
from spacemaker.application.reset_library import ResetLibrary
from spacemaker.application.sync_gallery_index import SyncGalleryIndex
from spacemaker.application.transfer_session import (
	SaveTransferItemToDocuments,
	StageTransferItem,
)
from spacemaker.application.transfer_usb_files import TransferUsbFiles
from spacemaker.bootstrap.bundled_tools import (
	BundledTool,
	ensure_host_tool_path_dirs,
	resolve_tool_path,
	tools_install_root,
)
from spacemaker.bootstrap.paths import (
	default_documents_receive_root,
	default_library_root,
	network_passcode_path,
	normalize_library_root,
	user_preferences_path,
)
from spacemaker.bootstrap.services.jobs import JobsMixin
from spacemaker.bootstrap.services.lan_sessions import LanSessionMixin
from spacemaker.bootstrap.services.managed_tools import ManagedToolsService
from spacemaker.bootstrap.services.repo import repo_root
from spacemaker.bootstrap.services.snapshots import SnapshotMixin
from spacemaker.bootstrap.services.usb_browse import UsbBrowseMixin
from spacemaker.domain.app_module import LanSessionKind
from spacemaker.domain.compress_media import CompressMediaPreference, resolve_compress_media_preference
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.extract_control import ExtractJobControl
from spacemaker.domain.gallery_export_job import GalleryExportJob
from spacemaker.domain.jobs import JobPhase
from spacemaker.domain.library import LibraryFolder
from spacemaker.domain.transfer_session import TransferSessionItem
from spacemaker.ports.outbound.device_repository import DeviceRepositoryPort


if TYPE_CHECKING:
	from fastapi import FastAPI

_T = TypeVar("_T")


class WebSocketLike(Protocol):
	async def send_json(self, data: dict[str, object]) -> None: ...


class AppServices(SnapshotMixin, LanSessionMixin, JobsMixin, UsbBrowseMixin):
	# None only for test doubles that skip __init__; the web middleware treats None as 'no passcode'.
	network_passcode: NetworkPasscode | None = None

	def __init__(self, *, port: int = 8765, bind_host: str = "0.0.0.0") -> None:
		ensure_host_tool_path_dirs()
		self.port = port
		self.bind_host = bind_host
		self.session = AppSession(library_root=normalize_library_root(default_library_root()))
		self.filesystem = LocalFileSystem()
		self.managed_tools = ManagedToolsService(
			CatalogToolInstaller(repo_root=repo_root()),
			dest_dir=tools_install_root(),
		)
		self.user_preferences = JsonUserPreferences(user_preferences_path())
		self.network_passcode = NetworkPasscode(
			JsonPasscodeStore(network_passcode_path()),
			ScryptPasscodeCrypto(),
			MonotonicClock(),
		)
		self.network_passcode.load()
		self.compression_tools = ManagedCompressionTools(self.managed_tools)
		self.runner = ToolRunner(path_fallback_allowed=self.managed_tools.permit_path_fallback)
		self.probe = SubprocessMediaProbe(self.runner)
		self.converter = SubprocessMediaConverter(self.runner)
		self.error_recovery = ErrorRecovery(self.filesystem)
		self.promote_originals = PromoteOriginalsToProcessed(self.filesystem)
		self.clear_user_preferences = ClearUserPreferences(self.user_preferences)
		self.clear_browser_cache = ClearBrowserCache(self.filesystem)
		self.gallery_index = SqliteGalleryIndex()
		self.reset_library = ResetLibrary(self.filesystem, self.gallery_index)
		self.sync_gallery_index = SyncGalleryIndex(self.filesystem, self.probe, self.gallery_index)
		self.gallery = GenerateGallery(self.gallery_index)
		self.get_gallery_item = GetGalleryItem(self.filesystem, self.probe)
		self.delete_gallery_item = DeleteGalleryItem(self.filesystem)
		self.export_friendly = ExportFriendlyMedia(self.filesystem, self.converter, self.probe)
		self.thumbnails = SubprocessThumbnailGenerator(self.runner)
		self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="spacemaker-job")
		# Friendly exports get their own worker so a long extract + convert can't starve a download.
		self._export_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="spacemaker-export")
		self._device_repos: dict[ConnectionMethod, DeviceRepositoryPort] = {}
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
		self._transfer_session_token: str = ""
		self._transfer_items: list[TransferSessionItem] = []
		self._transfer_staging_root: str = ""
		self._transfer_lock = threading.Lock()
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
		self.content_hasher = Sha256ContentHasher()
		self.stage_transfer = StageTransferItem(self.filesystem, self.content_hasher)
		self.save_transfer_to_documents = SaveTransferItemToDocuments(self.filesystem)
		self._documents_receive_root = default_documents_receive_root()

	def devices_for(self, method: ConnectionMethod) -> DeviceRepositoryPort:
		if method is ConnectionMethod.WIFI:
			raise ValueError("Wi-Fi extract does not use DeviceRepository")
		cached = self._device_repos.get(method)
		if cached is not None:
			return cached
		repo = device_repository_for(method, runner=self.runner)
		self._device_repos[method] = repo
		return repo

	def release_device_mounts(self) -> None:
		for repo in list(self._device_repos.values()):
			release = getattr(repo, "release_mounts", None)
			if callable(release):
				with contextlib.suppress(Exception):
					release()
		self._device_repos.clear()

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

	async def remove_gallery_item(self, library_root: str, relative_path: str) -> bool:
		removed = self.delete_gallery_item.run(library_root, relative_path)
		if removed:
			await self.gallery_index.remove(library_root, relative_path)
			self.push_state()
		return removed

	def run_coro(self, coro: Coroutine[object, object, _T]) -> _T:
		"""Bridge async gallery-index work from sync code onto an event loop.

		- Worker threads: ``run_coroutine_threadsafe`` against the bound ASGI loop.
		- No loop: ``asyncio.run``.
		- Already on a running loop (e.g. async upload → maybe_start_convert_drain):
			run the coroutine in a helper thread via ``asyncio.run`` so we never block
			the ASGI loop with ``.result()``.
		"""
		try:
			asyncio.get_running_loop()
		except RuntimeError:
			loop = self._event_loop
			if loop is not None and loop.is_running():
				return asyncio.run_coroutine_threadsafe(coro, loop).result()
			return asyncio.run(coro)

		from concurrent.futures import ThreadPoolExecutor

		def _runner() -> _T:
			return asyncio.run(coro)

		with ThreadPoolExecutor(max_workers=1, thread_name_prefix="spacemaker-aio") as pool:
			return pool.submit(_runner).result()

	def bind_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
		self._event_loop = loop

	def register_ws(self, ws: WebSocketLike) -> None:
		with self._ws_lock:
			self._ws_clients.add(ws)

	def unregister_ws(self, ws: WebSocketLike) -> None:
		with self._ws_lock:
			self._ws_clients.discard(ws)

	def with_lan_login(self, url: str) -> str:
		"""Append the QR sign-in token fragment to a phone URL while a passcode is set."""
		passcode = self.network_passcode
		token = passcode.qr_token() if passcode is not None else None
		return f"{url}#k={token}" if token else url

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
		self.release_device_mounts()
		self._clear_transfer_session()
		self._executor.shutdown(wait=False, cancel_futures=True)
		self._export_executor.shutdown(wait=False, cancel_futures=True)

	def compress_media_preference(self) -> CompressMediaPreference:
		return resolve_compress_media_preference(
			stored=self.user_preferences.get_compress_media(),
			tools_available=self.compression_tools.available(),
		)

	def set_compress_media(self, enabled: bool) -> CompressMediaPreference:
		"""Persist preference when tools allow; always return effective resolved state."""
		if self.compression_tools.available():
			self.user_preferences.set_compress_media(bool(enabled))
		return self.compress_media_preference()


def create_app(*, port: int = 8765, bind_host: str = "0.0.0.0") -> FastAPI:
	from spacemaker.adapters.inbound.web.app import create_fastapi_app

	services = AppServices(port=port, bind_host=bind_host)
	return create_fastapi_app(services)
