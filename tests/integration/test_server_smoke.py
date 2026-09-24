"""Launches the real `spacemaker` process (not TestClient) to catch startup bugs that
in-process tests can't see -- e.g. the uvicorn `loop=` factory wiring bug that silently
crashed the server's background thread while every TestClient-based test kept passing.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from socket import AF_INET, SOCK_STREAM, socket

import httpx
import pytest


pytestmark = pytest.mark.integration

STARTUP_TIMEOUT_SECONDS = 20


def _free_port() -> int:
	with socket(AF_INET, SOCK_STREAM) as sock:
		sock.bind(("127.0.0.1", 0))
		return sock.getsockname()[1]


def _read_output_into(process: subprocess.Popen, lines: list[str]) -> None:
	assert process.stdout is not None
	for line in process.stdout:
		lines.append(line)


def test_given_real_process_when_server_only_starts_then_boots_and_serves() -> None:
	port = _free_port()
	process = subprocess.Popen(
		[sys.executable, "-m", "spacemaker", "--server-only", "--port", str(port)],
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		text=True,
	)
	output: list[str] = []
	reader = threading.Thread(target=_read_output_into, args=(process, output), daemon=True)
	reader.start()

	try:
		ready = False
		deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
		while time.monotonic() < deadline and process.poll() is None:
			try:
				response = httpx.get(f"http://127.0.0.1:{port}/api/defaults", timeout=0.5)
			except httpx.TransportError:
				time.sleep(0.2)
				continue
			if response.status_code == 200:
				ready = True
				break

		exited_early = process.poll() is not None
		assert ready and not exited_early, (
			"spacemaker --server-only did not boot cleanly "
			f"(exited_early={exited_early}, exit_code={process.poll()}).\n"
			"--- full process output ---\n" + "".join(output) + "---------------------------"
		)

		index_response = httpx.get(f"http://127.0.0.1:{port}/", timeout=5)
		assert index_response.status_code == 200
	finally:
		process.terminate()
		try:
			process.wait(timeout=5)
		except subprocess.TimeoutExpired:
			process.kill()
			process.wait(timeout=5)
		reader.join(timeout=5)
