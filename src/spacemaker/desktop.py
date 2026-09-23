from __future__ import annotations

import argparse
import threading
import time
import webbrowser

import uvicorn
import webview
from webview.errors import WebViewException

from spacemaker.adapters.inbound.desktop_api import DesktopApi
from spacemaker.adapters.inbound.qt_webengine_shutdown import install_qt_webengine_shutdown_fix
from spacemaker.bootstrap.paths import webengine_storage_path
from spacemaker.bootstrap.services import create_app


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

	thread = threading.Thread(
		target=run_server,
		kwargs={"port": args.port, "host": args.host},
		daemon=True,
		name="spacemaker-uvicorn",
	)
	thread.start()

	url = f"http://127.0.0.1:{args.port}/"

	if args.server_only:
		thread.join()
		return

	time.sleep(0.3)
	install_qt_webengine_shutdown_fix()
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
