# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onefile spec — app + legal + static UI; no CLI tools."""

import sys
from pathlib import Path

repo = Path(SPECPATH).resolve().parent
src = repo / "src"
icon = repo / "packaging" / "assets" / "spacemaker-icon.png"

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
	console=False if sys.platform == "darwin" else True,
	disable_windowed_traceback=False,
	argv_emulation=False,
	target_arch=None,
	codesign_identity=None,
	entitlements_file=None,
	icon=str(icon) if icon.is_file() else None,
)
