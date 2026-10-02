from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from spacemaker.adapters.inbound.web.client_access import require_loopback
from spacemaker.adapters.inbound.web.media_paths import _LEGAL, _session_library_root
from spacemaker.adapters.inbound.web.models import LibraryOpenFolderBody, ModuleEnterBody, SettingsBody
from spacemaker.adapters.inbound.web.qr_svg import qr_svg_response
from spacemaker.adapters.outbound.host.open_paths import reveal_in_file_manager
from spacemaker.bootstrap.firewall import probe_gallery_port
from spacemaker.bootstrap.lan import lan_ip
from spacemaker.bootstrap.paths import (
	default_documents_receive_root,
	default_library_root,
	documents_directory,
	documents_folder_open_target,
	is_absolute_library_path,
	normalize_library_root,
	pictures_directory,
	webengine_storage_path,
)
from spacemaker.bootstrap.services import AppServices
from spacemaker.domain.app_module import AppModule
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.jobs import JobPhase
from spacemaker.domain.library import LibraryFolder, TransferMode
from spacemaker.domain.transfer_folders import merge_extra_paths
from spacemaker.domain.usb_file_transfer import default_transfer_folders


def build_settings_router(services: AppServices) -> APIRouter:
	router = APIRouter()

	@router.get("/api/server-info")
	def server_info() -> dict[str, object]:
		host = lan_ip()
		gallery_url = services.with_lan_login(f"http://{host}:{services.port}/gallery")
		lan_listening = services.bind_host in {"0.0.0.0", "::"}  # noqa: S104
		firewall = probe_gallery_port(services.port, bind_host=services.bind_host)
		return {
			"host": host,
			"port": services.port,
			"gallery_url": gallery_url,
			"qr_url": "/api/gallery/qr.svg",
			"lan_listening": lan_listening,
			"lan_reachable": lan_listening and host != "127.0.0.1",
			"firewall": {
				"backend": firewall.backend,
				"active": firewall.active,
				"port_open": firewall.port_open,
				"lan_connect_ok": firewall.lan_connect_ok,
				"message": firewall.message,
			},
		}

	@router.get("/api/gallery/qr.svg")
	def gallery_qr() -> Response:
		gallery_url = services.with_lan_login(f"http://{lan_ip()}:{services.port}/gallery")
		return qr_svg_response(gallery_url)

	@router.get("/api/defaults")
	def defaults(request: Request) -> dict[str, str]:
		require_loopback(request)
		root = default_library_root()
		return {
			"default_library_root": root,
			"pictures_directory": str(pictures_directory()),
			"documents_receive_root": default_documents_receive_root(),
		}

	@router.get("/api/settings")
	def get_settings(request: Request) -> dict[str, object]:
		require_loopback(request)
		return services.enriched_snapshot()

	@router.put("/api/settings")
	def put_settings(request: Request, body: SettingsBody) -> dict[str, object]:
		require_loopback(request)
		# Compress media may change during an active receive session.
		compress_changed = False
		if body.compress_media is not None:
			before = services.compress_media_preference().enabled
			after = services.set_compress_media(body.compress_media)
			compress_changed = after.enabled != before
		job_active = False
		with services.session._lock:
			if body.ui_mode is not None:
				services.session.ui_mode = body.ui_mode
			job_active = services.session.extract_phase in {
				JobPhase.RUNNING,
				JobPhase.PAUSED,
			} or services.session.usb_transfer_phase in {JobPhase.RUNNING, JobPhase.PAUSED}
			if not job_active:
				library_root = normalize_library_root(body.library_root)
				if library_root and not is_absolute_library_path(library_root):
					raise HTTPException(status_code=400, detail="library_root must be an absolute path")
				previous_method = services.session.connection_method
				services.session.library_root = library_root
				services.session.connection_method = body.connection_method
				if body.connection_method is ConnectionMethod.WIFI:
					services.session.transfer_mode = TransferMode.COPY
				else:
					services.session.transfer_mode = body.transfer_mode
				if body.connection_method is not previous_method:
					services.release_device_mounts()
					services.session.device_id = ""
					services.session.device_label = ""
					services.session.transfer_extra_paths = []
					if services.session.active_module is AppModule.USB_FILE_TRANSFER and body.transfer_folders is None:
						services.session.transfer_folders = sorted(
							f.value for f in default_transfer_folders(body.connection_method)
						)
				device_id = body.device_id.strip()
				if body.connection_method is ConnectionMethod.WIFI:
					services.session.device_id = ""
					services.session.device_label = ""
				else:
					try:
						repo = services.devices_for(body.connection_method)
						known = {d.device_id: d.label for d in repo.list_devices()}
					except (FileNotFoundError, RuntimeError, ValueError):
						known = {}
					if device_id and device_id in known:
						services.session.device_id = device_id
						services.session.device_label = known[device_id]
					else:
						services.session.device_id = ""
						services.session.device_label = ""
				if body.source_folders is not None:
					services.session.source_folders = [f.lower() for f in body.source_folders]
				if body.transfer_folders is not None:
					services.session.transfer_folders = [f.lower() for f in body.transfer_folders]
				if body.transfer_extra_paths is not None:
					services.session.transfer_extra_paths = merge_extra_paths([], body.transfer_extra_paths)
				if services.session.library_root:
					services.filesystem.ensure_library_folders(services.session.library_root)
		# Never call push_state()/maybe_start_convert_drain() while holding the (non-reentrant) session lock.
		if compress_changed:
			services.maybe_start_convert_drain()
		services.push_state()
		return services.enriched_snapshot()

	@router.post("/api/preferences/clear")
	def clear_preferences(request: Request) -> dict[str, object]:
		require_loopback(request)
		services.clear_user_preferences.run()
		services.maybe_start_convert_drain()
		services.push_state()
		return services.enriched_snapshot()

	@router.post("/api/browser-cache/clear")
	def clear_browser_cache(request: Request) -> dict[str, object]:
		require_loopback(request)
		services.clear_browser_cache.run(webengine_storage_path())
		return {"cleared": True}

	@router.post("/api/library/reset")
	async def reset_library(request: Request) -> dict[str, object]:
		require_loopback(request)
		root = _session_library_root(services)
		if not root:
			raise HTTPException(status_code=400, detail="library_root required")
		services.stop_convert_and_wait(timeout_seconds=30.0)
		await services.reset_library.run(root)
		services.push_state()
		return services.enriched_snapshot()

	@router.post("/api/easy/bootstrap")
	def easy_bootstrap(request: Request) -> dict[str, object]:
		require_loopback(request)
		if not services.session.library_root or not is_absolute_library_path(services.session.library_root):
			raise HTTPException(status_code=400, detail="choose a valid library folder")
		services.ensure_easy_session()
		return services.enriched_snapshot()

	@router.post("/api/module/enter")
	def module_enter(request: Request, body: ModuleEnterBody) -> dict[str, object]:
		require_loopback(request)
		if body.module in {AppModule.PHOTO_BACKUP, AppModule.USB_PHOTO_BACKUP}:
			if not services.session.library_root or not is_absolute_library_path(services.session.library_root):
				raise HTTPException(status_code=400, detail="choose a valid library folder")
		services.enter_module(body.module)
		return services.enriched_snapshot()

	@router.post("/api/module/home")
	def module_home(request: Request) -> dict[str, object]:
		require_loopback(request)
		services.leave_module_for_home()
		return services.enriched_snapshot()

	@router.post("/api/documents/open-folder")
	def open_documents_folder(request: Request) -> dict[str, bool]:
		require_loopback(request)
		primary = documents_folder_open_target()
		fallback = documents_directory()
		try:
			reveal_in_file_manager(str(primary))
		except (OSError, FileNotFoundError):
			if primary.resolve() == fallback.resolve():
				raise HTTPException(status_code=500, detail="Could not open Documents folder") from None
			try:
				reveal_in_file_manager(str(fallback))
			except (OSError, FileNotFoundError) as exc:
				raise HTTPException(status_code=500, detail=str(exc)) from exc
		return {"ok": True}

	@router.post("/api/library/open-folder")
	def open_library_folder(request: Request, body: LibraryOpenFolderBody) -> dict[str, bool]:
		require_loopback(request)
		bucket = body.bucket.strip().lower()
		if bucket not in {"error", "invalid"}:
			raise HTTPException(status_code=400, detail="unknown bucket")
		root = services.session.library_root
		if not root or not is_absolute_library_path(root):
			raise HTTPException(status_code=400, detail="library not configured")
		folder = LibraryFolder.ERROR if bucket == "error" else LibraryFolder.INVALID
		target = Path(services.filesystem.library_path(root, folder, ""))
		target.mkdir(parents=True, exist_ok=True)
		try:
			reveal_in_file_manager(str(target))
		except OSError as exc:
			raise HTTPException(status_code=500, detail=str(exc)) from exc
		return {"ok": True}

	@router.get("/api/legal/{doc_id}")
	def legal_doc(doc_id: str) -> dict[str, str]:
		path = _LEGAL.get(doc_id)
		if path is None or not path.is_file():
			raise HTTPException(status_code=404, detail="unknown legal document")
		return {"id": doc_id, "markdown": path.read_text(encoding="utf-8")}

	return router
