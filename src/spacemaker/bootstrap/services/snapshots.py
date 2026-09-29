from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
	from spacemaker.bootstrap.services.core import AppServices

from spacemaker.application.library_image_issues import count_image_files_in_library_folder
from spacemaker.application.wizard_state import wizard_actions
from spacemaker.bootstrap.app_meta import app_release_info
from spacemaker.bootstrap.paths import default_library_root, display_user_path
from spacemaker.bootstrap.ui_shell import UI_SHELL_VERSION
from spacemaker.domain.app_module import LanSessionKind
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.jobs import JobPhase
from spacemaker.domain.library import LibraryFolder
from spacemaker.domain.transfer_session import TransferOrigin, TransferSessionItem
from spacemaker.domain.usb_file_transfer import (
	can_start_usb_file_transfer,
	shows_iphone_limit_banner,
	transfer_control_flags,
)
from spacemaker.domain.video_encode import HardwareVideoEncoder


class SnapshotMixin:
	def enriched_snapshot(self: AppServices) -> dict[str, object]:
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
		base["transfer_files_session"] = self._transfer_files_snapshot()
		base["documents_receive_root"] = self._documents_receive_root
		base["documents_receive_root_display"] = display_user_path(
			self._documents_receive_root,
			trailing_slash=True,
		)
		base["documents_receive_file_count"] = self._documents_receive_file_count()
		with self.session._lock:
			usb_phase = self.session.usb_transfer_phase
			usb_folders = list(self.session.transfer_folders)
			usb_extras = list(self.session.transfer_extra_paths)
			usb_has_device = bool(self.session.device_id)
			usb_method = self.session.connection_method
			usb_device_id = self.session.device_id
			usb_completed = self.session.usb_transfer_progress.completed
		usb_flags = transfer_control_flags(usb_phase)
		usb_flags["start"] = can_start_usb_file_transfer(
			has_device=usb_has_device,
			folders_selected=len(usb_folders) > 0,
			extras_selected=len(usb_extras) > 0,
			phase=usb_phase,
		)
		base["usb_transfer_actions"] = usb_flags
		base["usb_transfer_iphone_limit"] = shows_iphone_limit_banner(usb_method)
		base["usb_transfer_show_open_folder"] = (
			usb_phase in {JobPhase.DONE, JobPhase.STOPPED} and usb_completed > 0
		) or self._documents_receive_file_count() > 0
		browse = self._usb_browse_snapshot(usb_method, usb_device_id)
		base["usb_transfer_browse"] = browse
		base["usb_transfer_available_folders"] = browse["available_folders"]
		base["transfer_extra_paths"] = usb_extras
		if library_root:
			base["library_root_display"] = display_user_path(library_root, trailing_slash=True)
		else:
			base["library_root_display"] = display_user_path(default_library_root(), trailing_slash=True)
		base["share_selection"] = list(self._share_selection)
		base["ui_shell_version"] = UI_SHELL_VERSION
		compress = self.compress_media_preference()
		base["compress_media"] = {
			"enabled": compress.enabled,
			"control_enabled": compress.control_enabled,
			"tools_available": compress.tools_available,
		}
		base.update(app_release_info())
		return base

	def _wifi_upload_snapshot(self: AppServices) -> dict[str, object]:
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

	def _receive_files_snapshot(self: AppServices) -> dict[str, object]:
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

	def _file_share_snapshot(self: AppServices) -> dict[str, object]:
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

	def _transfer_files_snapshot(self: AppServices) -> dict[str, object]:
		from spacemaker.bootstrap.lan import lan_ip

		with self._wifi_token_lock:
			token = self._transfer_session_token
			kind = self._lan_session_kind
		with self._transfer_lock:
			items = list(self._transfer_items)
		active = kind is LanSessionKind.TRANSFER_FILES and bool(token)
		if not active:
			return {"active": False, "page_url": "", "qr_url": "", "item_count": 0, "items": []}
		host = lan_ip()
		page_url = f"http://{host}:{self.port}/transfer?t={token}"
		return {
			"active": True,
			"page_url": page_url,
			"qr_url": f"/api/transfer/qr.svg?t={token}",
			"item_count": len(items),
			"items": [self._transfer_item_row(item) for item in items],
		}

	def _transfer_item_row(self: AppServices, item: TransferSessionItem) -> dict[str, str]:
		origin_label = "PC" if item.origin is TransferOrigin.PC else "Phone"
		return {
			"id": item.file_id,
			"name": item.display_name,
			"kind": item.kind.value,
			"origin": item.origin.value,
			"origin_label": origin_label,
			"download_name": item.display_name,
		}
