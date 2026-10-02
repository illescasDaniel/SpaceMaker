from __future__ import annotations

from pydantic import BaseModel

from spacemaker.domain.app_module import AppModule
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.library import TransferMode
from spacemaker.domain.ui_mode import UiMode


class PasscodeBody(BaseModel):
	passcode: str


class UnlockBody(BaseModel):
	passcode: str | None = None
	token: str | None = None


class GalleryExportBody(BaseModel):
	relative_path: str
	format: str


class GalleryOpenBody(BaseModel):
	relative_path: str
	target: str


class ModuleEnterBody(BaseModel):
	module: AppModule


class ShareSelectionBody(BaseModel):
	paths: list[str]


class TransferAddBody(BaseModel):
	paths: list[str]


class TransferSaveBody(BaseModel):
	file_id: str


class LibraryOpenFolderBody(BaseModel):
	bucket: str


class SettingsBody(BaseModel):
	library_root: str = ""
	ui_mode: UiMode | None = None
	connection_method: ConnectionMethod = ConnectionMethod.WIFI
	transfer_mode: TransferMode = TransferMode.COPY
	device_id: str = ""
	device_label: str = ""
	source_folders: list[str] | None = None
	transfer_folders: list[str] | None = None
	transfer_extra_paths: list[str] | None = None
	compress_media: bool | None = None


class UsbTransferExtrasBody(BaseModel):
	host_paths: list[str] = []
