from spacemaker.adapters.inbound.web.spa_entry import SpaEntry, spa_entry_for


def test_given_loopback_when_spa_entry_for_gallery_then_desktop():
	assert spa_entry_for(host="127.0.0.1", path="/gallery") is SpaEntry.DESKTOP


def test_given_lan_host_when_spa_entry_for_gallery_then_mobile_gallery():
	assert spa_entry_for(host="192.168.1.42", path="/gallery") is SpaEntry.MOBILE_GALLERY


def test_given_lan_host_when_spa_entry_for_gallery_item_then_mobile_gallery():
	assert spa_entry_for(host="192.168.1.42", path="/gallery/item/foo.avif") is SpaEntry.MOBILE_GALLERY


def test_given_lan_host_when_spa_entry_for_root_then_mobile_remote():
	assert spa_entry_for(host="192.168.1.42", path="/") is SpaEntry.MOBILE_REMOTE


def test_given_test_client_host_when_spa_entry_for_gallery_then_desktop():
	assert spa_entry_for(host="testserver", path="/gallery") is SpaEntry.DESKTOP
