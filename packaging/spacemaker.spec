# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — app + legal + static UI; no CLI tools.

Windows: onefile SpaceMaker.exe.
macOS: onedir + BUNDLE → SpaceMaker.app (packaged into a DMG by build_macos_dmg.sh).
"""

import sys
import tomllib
from pathlib import Path

repo = Path(SPECPATH).resolve().parent
src = repo / "src"
icon_png = repo / "packaging" / "assets" / "spacemaker-icon.png"
icon_icns = repo / "packaging" / "assets" / "spacemaker.icns"
_version = tomllib.load((repo / "pyproject.toml").open("rb"))["project"]["version"]

block_cipher = None

# Native pywebview backend per OS (edgechromium=Windows, cocoa=macOS); Qt WebEngine
# is Linux-only (bundled there via the AppImage flow, not this onefile spec) — never
# bundle backends other than the one this build's OS actually uses.
_unused_gui_backends = {
	"win32": ["webview.platforms.cocoa", "webview.platforms.gtk", "webview.platforms.qt"],
	"darwin": ["webview.platforms.edgechromium", "webview.platforms.gtk", "webview.platforms.qt"],
}.get(sys.platform, ["webview.platforms.cocoa", "webview.platforms.edgechromium"])

a = Analysis(
	[str(repo / "src" / "spacemaker" / "desktop.py")],
	pathex=[str(src)],
	binaries=[],
	datas=[
		(str(repo / "docs" / "legal"), "docs/legal"),
		(str(repo / "packaging" / "tool-catalog.json"), "packaging"),
		(str(repo / "packaging" / "assets" / "spacemaker-icon.png"), "packaging/assets"),
		(
			str(repo / "src" / "spacemaker" / "adapters" / "inbound" / "web" / "static"),
			"spacemaker/adapters/inbound/web/static",
		),
	],
	hiddenimports=["spacemaker"],
	hookspath=[],
	hooksconfig={},
	runtime_hooks=[],
	excludes=[
		"webview.platforms.cef",
		"webview.platforms.mshtml",
		"webview.platforms.winforms",
		*_unused_gui_backends,
	],
	win_no_prefer_redirects=False,
	win_private_assemblies=False,
	cipher=block_cipher,
	noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

_is_macos = sys.platform == "darwin"
_exe_icon = None
if _is_macos and icon_icns.is_file():
	_exe_icon = str(icon_icns)
elif icon_png.is_file():
	_exe_icon = str(icon_png)

if _is_macos:
	exe = EXE(
		pyz,
		a.scripts,
		[],
		exclude_binaries=True,
		name="SpaceMaker",
		debug=False,
		bootloader_ignore_signals=False,
		strip=False,
		upx=False,
		console=False,
		disable_windowed_traceback=False,
		argv_emulation=False,
		target_arch=None,
		codesign_identity=None,
		entitlements_file=None,
		icon=_exe_icon,
	)
	coll = COLLECT(
		exe,
		a.binaries,
		a.zipfiles,
		a.datas,
		strip=False,
		upx=False,
		upx_exclude=[],
		name="SpaceMaker",
	)
	app = BUNDLE(
		coll,
		name="SpaceMaker.app",
		icon=_exe_icon,
		bundle_identifier="eu.daniel-ir.spacemaker",
		info_plist={
			"CFBundleName": "SpaceMaker",
			"CFBundleDisplayName": "SpaceMaker",
			"CFBundlePackageType": "APPL",
			"CFBundleShortVersionString": _version,
			"CFBundleVersion": _version,
			"NSHighResolutionCapable": True,
			"LSMinimumSystemVersion": "11.0",
		},
	)
else:
	exe = EXE(
		pyz,
		a.scripts,
		a.binaries,
		a.zipfiles,
		a.datas,
		[],
		name="SpaceMaker",
		debug=False,
		bootloader_ignore_signals=False,
		strip=False,
		upx=False,
		upx_exclude=[],
		runtime_tmpdir=None,
		console=True,
		disable_windowed_traceback=False,
		argv_emulation=False,
		target_arch=None,
		codesign_identity=None,
		entitlements_file=None,
		icon=_exe_icon,
	)
