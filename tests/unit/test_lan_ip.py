from spacemaker.bootstrap.lan import lan_ip, local_ipv4_addresses


def test_given_local_ipv4_addresses_when_lan_ip_then_not_empty_string():
	# given
	# when
	ip = lan_ip()
	# then
	assert ip
	assert isinstance(ip, str)


def test_given_hostname_when_local_ipv4_addresses_then_returns_list():
	# given
	# when
	addresses = local_ipv4_addresses()
	# then
	assert isinstance(addresses, list)
