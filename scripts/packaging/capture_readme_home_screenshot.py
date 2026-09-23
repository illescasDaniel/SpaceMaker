#!/usr/bin/env python3
"""Capture the SpaceMaker Home hub for README (offscreen Qt WebEngine)."""

from __future__ import annotations

import argparse
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

from spacemaker.bootstrap.ui_shell import UI_SHELL_VERSION


_REPO = Path(__file__).resolve().parents[2]
_DEFAULT_OUTPUT = _REPO / "docs" / "assets" / "readme-home.png"
_VIEW_WIDTH = 980
_VIEW_HEIGHT = 920
_HTTP_TIMEOUT = httpx.Timeout(5.0, connect=2.0)
_SERVER_WAIT_S = 45.0
_HOME_WAIT_S = 30.0


def _ephemeral_port() -> int:
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
		sock.bind(("127.0.0.1", 0))
		return int(sock.getsockname()[1])


def _wait_for_http(base: str, *, deadline: float) -> None:
	while time.monotonic() < deadline:
		try:
			response = httpx.get(f"{base}/", timeout=_HTTP_TIMEOUT)
			if response.status_code == 200:
				return
		except httpx.HTTPError:
			pass
		time.sleep(0.25)
	raise RuntimeError(f"Timed out waiting for SpaceMaker HTTP at {base}")


def _prepare_smoke_home() -> Path:
	home = Path(tempfile.mkdtemp(prefix="spacemaker-readme-shot."))
	for name in ("Documents", "Pictures", ".local/share", ".config", ".cache"):
		(home / name).mkdir(parents=True, exist_ok=True)
	return home


def _server_env(home: Path) -> dict[str, str]:
	env = os.environ.copy()
	env["HOME"] = str(home)
	env["SPACEMAKER_DEV"] = "1"
	env.setdefault("QT_QPA_PLATFORM", "offscreen")
	env["XDG_DATA_HOME"] = str(home / ".local" / "share")
	env["XDG_CONFIG_HOME"] = str(home / ".config")
	env["XDG_CACHE_HOME"] = str(home / ".cache")
	return env


def _start_server(port: int, env: dict[str, str]) -> subprocess.Popen[bytes]:
	cmd = [
		sys.executable,
		"-m",
		"spacemaker.desktop",
		"--server-only",
		"--host",
		"127.0.0.1",
		"--port",
		str(port),
	]
	return subprocess.Popen(
		cmd,
		env=env,
		cwd=_REPO,
		stdout=subprocess.DEVNULL,
		stderr=subprocess.PIPE,
	)


def _bypass_components_setup(base: str) -> None:
	response = httpx.post(f"{base}/api/tools/components-continue", timeout=_HTTP_TIMEOUT)
	response.raise_for_status()
	payload = response.json()
	if payload.get("setup_pending"):
		raise RuntimeError("Components setup still pending after POST /api/tools/components-continue")


def _capture_with_webengine(url: str, output: Path) -> None:
	try:
		from PyQt6.QtCore import QEventLoop, QTimer, QUrl
		from PyQt6.QtWebEngineWidgets import QWebEngineView
		from PyQt6.QtWidgets import QApplication
	except ImportError as exc:
		raise RuntimeError(
			"PyQt6 WebEngine is required (install project deps: uv run task sync-dev). "
			"If headless capture fails, try QT_QPA_PLATFORM=xcb.",
		) from exc

	app = QApplication.instance()
	if app is None:
		app = QApplication(sys.argv)

	view = QWebEngineView()
	view.resize(_VIEW_WIDTH, _VIEW_HEIGHT)
	view.show()

	loop = QEventLoop()
	deadline = time.monotonic() + _HOME_WAIT_S
	home_ready = False
	load_done = False
	saved = False

	def fail(message: str) -> None:
		if loop.isRunning():
			loop.quit()
		raise RuntimeError(message)

	def poll_home() -> None:
		nonlocal home_ready
		if home_ready or time.monotonic() >= deadline:
			if not home_ready:
				fail("Timed out waiting for #view-home to become active")
			return

		def on_result(active: object) -> None:
			nonlocal home_ready
			if active is True:
				home_ready = True
				QTimer.singleShot(800, save_png)
			else:
				QTimer.singleShot(200, poll_home)

		view.page().runJavaScript(
			'document.getElementById("view-home")?.classList.contains("active") === true',
			on_result,
		)

	def save_png() -> None:
		nonlocal saved
		if saved:
			return
		image = view.grab().toImage()
		if image.isNull():
			fail("WebEngine grab returned an empty image")
		output.parent.mkdir(parents=True, exist_ok=True)
		if not image.save(str(output), "PNG"):
			fail(f"Could not write {output}")
		saved = True
		if loop.isRunning():
			loop.quit()

	def on_load_ok(ok: bool) -> None:
		nonlocal load_done
		load_done = ok
		if not ok:
			fail(f"Failed to load {url}")
		QTimer.singleShot(500, poll_home)

	view.loadFinished.connect(on_load_ok)
	view.load(QUrl(url))

	QTimer.singleShot(int(_HOME_WAIT_S * 1000), lambda: fail("Capture timed out"))
	loop.exec()

	if not saved:
		fail("Capture did not complete")
	if not load_done:
		fail("Page load did not finish")


def _terminate_server(proc: subprocess.Popen[bytes]) -> None:
	if proc.poll() is not None:
		return
	proc.send_signal(signal.SIGTERM)
	try:
		proc.wait(timeout=8)
	except subprocess.TimeoutExpired:
		proc.kill()
		proc.wait(timeout=5)


def main(argv: list[str] | None = None) -> int:
	parser = argparse.ArgumentParser(description="Capture SpaceMaker Home hub PNG for the README.")
	parser.add_argument(
		"--output",
		type=Path,
		default=_DEFAULT_OUTPUT,
		help=f"PNG path (default: {_DEFAULT_OUTPUT.relative_to(_REPO)})",
	)
	parser.add_argument("--port", type=int, default=0, help="Server port (0 = ephemeral)")
	parser.add_argument(
		"--keep-server",
		action="store_true",
		help="Leave server running after capture (debug)",
	)
	args = parser.parse_args(argv)

	port = args.port or _ephemeral_port()
	base = f"http://127.0.0.1:{port}"
	shell_query = UI_SHELL_VERSION.replace(".", "-")
	url = f"{base}/?_shell={shell_query}"

	smoke_home = _prepare_smoke_home()
	env = _server_env(smoke_home)
	proc = _start_server(port, env)

	try:
		_wait_for_http(base, deadline=time.monotonic() + _SERVER_WAIT_S)
		if proc.poll() is not None:
			err = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
			raise RuntimeError(f"SpaceMaker server exited early.\n{err}".strip())

		_bypass_components_setup(base)
		_capture_with_webengine(url, args.output.resolve())
	except Exception as exc:
		if proc.stderr is not None:
			err_tail = proc.stderr.read().decode("utf-8", errors="replace").strip()
			if err_tail:
				print(err_tail, file=sys.stderr)
		print(f"error: {exc}", file=sys.stderr)
		return 1
	finally:
		if not args.keep_server:
			_terminate_server(proc)
		else:
			print(f"Server still running at {base} (pid {proc.pid})", file=sys.stderr)

	print(f"Wrote {args.output}")
	return 0


if __name__ == "__main__":
	sys.exit(main())
