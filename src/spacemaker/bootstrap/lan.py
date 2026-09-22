from __future__ import annotations

import socket


def local_ipv4_addresses() -> list[str]:
	addresses: list[str] = []
	try:
		hostname = socket.gethostname()
		for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
			ip = str(info[4][0])
			if ip not in addresses:
				addresses.append(ip)
	except OSError:
		return []
	return addresses


def lan_ip() -> str:
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		sock.connect(("8.8.8.8", 80))
		ip = sock.getsockname()[0]
		if ip and not ip.startswith("127."):
			return ip
	except OSError:
		pass
	finally:
		sock.close()
	for ip in local_ipv4_addresses():
		if ip.startswith("127.") or ip.startswith("169.254."):
			continue
		return ip
	return "127.0.0.1"
