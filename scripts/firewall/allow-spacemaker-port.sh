#!/usr/bin/env bash
# Allow SpaceMaker LAN gallery (default TCP 8765) through common Linux firewalls.
set -euo pipefail

PORT="${1:-8765}"
RULE_COMMENT="SpaceMaker LAN gallery"

if [[ "${EUID}" -ne 0 ]]; then
	echo "This script must run as root (e.g. sudo $0 ${PORT})." >&2
	exit 1
fi

if command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
	firewall-cmd --permanent --add-port="${PORT}/tcp"
	firewall-cmd --reload
	echo "firewalld: allowed ${PORT}/tcp"
	exit 0
fi

if command -v ufw >/dev/null 2>&1; then
	ufw allow "${PORT}/tcp" comment "${RULE_COMMENT}"
	echo "ufw: allowed ${PORT}/tcp"
	ufw status numbered | grep -E "${PORT}/tcp|${PORT} " || true
	exit 0
fi

echo "No firewalld or ufw found." >&2
echo "On KDE Plasma: System Settings → Network → Firewall → add inbound TCP ${PORT}." >&2
echo "Or with nftables, add an input rule accepting tcp dport ${PORT}." >&2
exit 1
