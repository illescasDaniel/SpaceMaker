from __future__ import annotations

import argparse
import socket
import sys
import threading
import time
import webbrowser

import uvicorn
import webview
from webview.errors import WebViewException

from spacemaker.adapters.inbound.desktop_api import DesktopApi
from spacemaker.adapters.inbound.qt_webengine_shutdown import install_qt_webengine_shutdown_fix
from spacemaker.bootstrap.paths import app_icon_path, webengine_storage_path
from spacemaker.bootstrap.services import create_app
from spacemaker.bootstrap.ui_shell import UI_SHELL_VERSION


def _apply_qt_window_icon() -> None:
	icon = app_icon_path()
	if icon is None:
		return
	try:
		from typing import cast

		from qtpy.QtGui import QIcon
		from qtpy.QtWidgets import QApplication

		app = cast(QApplication, QApplication.instance())
		if app is not None:
			app.setWindowIcon(QIcon(str(icon)))
	except ImportError:
		return


def _port_in_use(port: int) -> bool:
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
		sock.settimeout(0.4)
		return sock.connect_ex(("127.0.0.1", port)) == 0


def run_server(*, port: int, host: str) -> None:
	app = create_app(port=port, bind_host=host)
	uvicorn.run(app, host=host, port=port, log_level="info")


def main(argv: list[str] | None = None) -> None:
	parser = argparse.ArgumentParser(prog="spacemaker")
	parser.add_argument("--port", type=int, default=8765)
	parser.add_argument("--host", default="0.0.0.0", help="Bind host (0.0.0.0 enables LAN gallery)")
	parser.add_argument("--server-only", action="store_true", help="Run API/UI in browser without pywebview")
	parser.add_argument(
		"--gui",
		choices=("qt", "gtk", "auto"),
		default="qt",
		help="pywebview backend (default qt for cross-platform packaging)",
	)
	args = parser.parse_args(argv)

	if _port_in_use(args.port):
		print(
			f"Port {args.port} is already in use — an old SpaceMaker server is probably still running.",
			file=sys.stderr,
		)
		print(
			"Stop it (close other SpaceMaker windows or free the port), then run again.",
			file=sys.stderr,
		)
		print(f"Or use another port: uv run spacemaker --port {args.port + 1}", file=sys.stderr)
		sys.exit(1)

	thread = threading.Thread(
		target=run_server,
		kwargs={"port": args.port, "host": args.host},
		daemon=True,
		name="spacemaker-uvicorn",
	)
	thread.start()

	shell_query = UI_SHELL_VERSION.replace(".", "-")
	url = f"http://127.0.0.1:{args.port}/?_shell={shell_query}"

	if args.server_only:
		thread.join()
		return

	time.sleep(0.3)
	install_qt_webengine_shutdown_fix()
	_apply_qt_window_icon()
	webview.create_window(
		"SpaceMaker",
		url,
		js_api=DesktopApi(),
		width=980,
		height=920,
		min_size=(720, 680),
	)
	gui = None if args.gui == "auto" else args.gui
	try:
		webview.start(
			gui=gui,
			private_mode=False,
			storage_path=webengine_storage_path(),
		)
	except WebViewException as exc:
		print(f"Desktop window unavailable ({exc}). Opening {url} in your browser.")
		webbrowser.open(url)
		thread.join()


if __name__ == "__main__":
	main()
