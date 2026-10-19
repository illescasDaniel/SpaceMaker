from spacemaker.adapters.inbound.web.spa_entry import SpaEntry, spa_entry_for


def test_given_loopback_client_when_gallery_then_desktop():
	assert spa_entry_for(client_host="127.0.0.1", path="/gallery") is SpaEntry.DESKTOP


def test_given_loopback_client_when_root_then_desktop():
	assert spa_entry_for(client_host="::1", path="/") is SpaEntry.DESKTOP


def test_given_lan_client_when_gallery_then_mobile_gallery():
	assert spa_entry_for(client_host="192.168.1.42", path="/gallery") is SpaEntry.MOBILE_GALLERY


def test_given_lan_client_when_gallery_item_then_mobile_gallery():
	assert spa_entry_for(client_host="192.168.1.42", path="/gallery/item/foo.avif") is SpaEntry.MOBILE_GALLERY


def test_given_lan_client_when_root_then_notice_page():
	assert spa_entry_for(client_host="192.168.1.42", path="/") is SpaEntry.MOBILE_REMOTE


def test_given_public_address_client_when_root_then_notice_page_not_desktop():
	assert spa_entry_for(client_host="8.8.8.8", path="/") is SpaEntry.MOBILE_REMOTE


def test_given_unknown_client_when_root_then_notice_page():
	assert spa_entry_for(client_host=None, path="/") is SpaEntry.MOBILE_REMOTE
