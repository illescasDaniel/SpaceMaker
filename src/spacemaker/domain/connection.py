from __future__ import annotations

from enum import StrEnum


class ConnectionMethod(StrEnum):
	WIFI = "wifi"
	ADB = "adb"
	AFC = "afc"
