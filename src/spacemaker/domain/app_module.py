from __future__ import annotations

from enum import StrEnum


class AppModule(StrEnum):
	HOME = "home"
	PHOTO_BACKUP = "photo_backup"
	USB_PHOTO_BACKUP = "usb_photo_backup"
	USB_FILE_TRANSFER = "usb_file_transfer"
	RECEIVE_FILES = "receive_files"
	SEND_FILES = "send_files"


class LanSessionKind(StrEnum):
	NONE = "none"
	PHOTO_UPLOAD = "photo_upload"
	RECEIVE_FILES = "receive_files"
	SEND_FILES = "send_files"
