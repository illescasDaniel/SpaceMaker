from __future__ import annotations

import re
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path

from spacemaker.bootstrap.lan import lan_ip


@dataclass(frozen=True, slots=True)
class FirewallStatus:
	backend: str | None
	active: bool | None
	port_open: bool | None
	lan_connect_ok: bool | None
	message: str


def _try_tcp_connect(host: str, port: int, *, timeout: float = 0.8) -> bool:
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.settimeout(timeout)
	try:
		sock.connect((host, port))
		return True
	except OSError:
		return False
	finally:
		sock.close()


def _lan_connect_probe(port: int) -> bool | None:
	host = lan_ip()
	if host.startswith("127."):
		return None
	loopback_ok = _try_tcp_connect("127.0.0.1", port)
	lan_ok = _try_tcp_connect(host, port)
	if loopback_ok and not lan_ok:
		return False
	if lan_ok:
		return True
	return None


def _firewalld_port_open(port: int) -> bool | None:
	try:
		state = subprocess.run(
			["firewall-cmd", "--state"],
			check=False,
			capture_output=True,
			text=True,
			timeout=2,
		)
	except (FileNotFoundError, subprocess.TimeoutExpired):
		return None
	if state.returncode != 0 or "running" not in (state.stdout or "").lower():
		return None
	try:
		query = subprocess.run(
			["firewall-cmd", "--query-port", f"{port}/tcp"],
			check=False,
			timeout=2,
		)
	except (FileNotFoundError, subprocess.TimeoutExpired):
		return None
	return query.returncode == 0


def _ufw_config_enabled() -> bool | None:
	path = Path("/etc/ufw/ufw.conf")
	if not path.is_file():
		return None
	for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
		stripped = line.strip()
		if stripped.startswith("ENABLED="):
			return stripped.split("=", 1)[-1].strip().lower() == "yes"
	return None


def _ufw_rules_mention_port(port: int) -> bool | None:
	path = Path("/etc/ufw/user.rules")
	if not path.is_file():
		return None
	text = path.read_text(encoding="utf-8", errors="ignore")
	patterns = (
		rf"dport {port}\b",
		rf"dport {port}/tcp",
		rf"PORT={port}\b",
	)
	return any(re.search(p, text) for p in patterns)


def probe_gallery_port(port: int, *, bind_host: str) -> FirewallStatus:
	lan_connect = _lan_connect_probe(port)
	firewalld_open = _firewalld_port_open(port)
	ufw_enabled = _ufw_config_enabled()
	ufw_has_rule = _ufw_rules_mention_port(port) if ufw_enabled else None

	backend: str | None = None
	active: bool | None = None
	port_open: bool | None = None
	message = ""

	if firewalld_open is not None:
		backend = "firewalld"
		active = True
		port_open = firewalld_open
		if not firewalld_open:
			message = f"firewalld is running but TCP {port} is not allowed in the active zone."
	elif ufw_enabled is not None:
		backend = "ufw"
		active = ufw_enabled
		if ufw_enabled:
			if ufw_has_rule is True:
				port_open = True
			elif ufw_has_rule is False:
				port_open = False
				message = f"UFW is enabled but no rule found for TCP {port}."
			else:
				port_open = None
				message = f"UFW is enabled; could not read rules for TCP {port} (may need root)."
		else:
			port_open = None
			message = "UFW is installed but disabled."

	if lan_connect is False:
		port_open = False if port_open is not False else port_open
		if bind_host in {"0.0.0.0", "::"}:  # noqa: S104
			hint = (
				f"This PC accepts LAN connections on port {port}, but a connection to your "
				f"LAN address failed. A host firewall may be blocking inbound TCP {port}."
			)
			message = hint if not message else f"{message} {hint}"
	elif lan_connect is True and port_open is None:
		port_open = True

	if port_open is None and not message:
		message = (
			"If your phone cannot load the gallery, allow inbound TCP "
			f"{port} in your firewall (UFW, firewalld, or KDE Plasma Firewall)."
		)

	return FirewallStatus(
		backend=backend,
		active=active,
		port_open=port_open,
		lan_connect_ok=lan_connect,
		message=message.strip(),
	)
