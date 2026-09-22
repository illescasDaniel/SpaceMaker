from spacemaker.bootstrap.firewall import FirewallStatus, probe_gallery_port


def test_given_unknown_backend_when_probe_then_returns_status(monkeypatch):
	# given
	monkeypatch.setattr("spacemaker.bootstrap.firewall._firewalld_port_open", lambda _p: None)
	monkeypatch.setattr("spacemaker.bootstrap.firewall._ufw_config_enabled", lambda: None)
	monkeypatch.setattr("spacemaker.bootstrap.firewall._lan_connect_probe", lambda _p: None)
	# when
	status = probe_gallery_port(8765, bind_host="0.0.0.0")  # noqa: S104
	# then
	assert isinstance(status, FirewallStatus)
	assert status.port_open is None


def test_given_lan_connect_fails_when_probe_then_port_likely_blocked(monkeypatch):
	# given
	monkeypatch.setattr("spacemaker.bootstrap.firewall._firewalld_port_open", lambda _p: None)
	monkeypatch.setattr("spacemaker.bootstrap.firewall._ufw_config_enabled", lambda: False)
	monkeypatch.setattr("spacemaker.bootstrap.firewall._lan_connect_probe", lambda _p: False)
	# when
	status = probe_gallery_port(8765, bind_host="0.0.0.0")  # noqa: S104
	# then
	assert status.port_open is False
	assert "firewall" in status.message.lower() or "LAN" in status.message
