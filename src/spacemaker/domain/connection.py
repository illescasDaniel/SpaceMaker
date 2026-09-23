from __future__ import annotations

from enum import StrEnum


class ConnectionMethod(StrEnum):
	WIFI = "wifi"
	MTP = "mtp"
	ADB = "adb"
	AFC = "afc"
