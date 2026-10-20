# Video posters, stream tokens (SPEC "Video posters — trust boundary"): random >= 128-bit url-safe tokens,
# each bound to one grant; resolve / revoke; revoked or unknown -> None.
import base64
import re

from spacemaker.application.device_stream_tokens import DeviceStreamTokens
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.device_stream import DeviceStreamGrant


def _grant(path: str = "DCIM/Camera/clip.mp4") -> DeviceStreamGrant:
	return DeviceStreamGrant(ConnectionMethod.ADB, "dev1", path, 9_000_000)


def test_given_grant_when_mint_then_token_is_urlsafe_and_at_least_128_bits() -> None:
	# given
	tokens = DeviceStreamTokens()
	# when
	token = tokens.mint(_grant())
	# then
	assert re.fullmatch(r"[A-Za-z0-9_-]+", token)
	raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
	assert len(raw) >= 16


def test_given_many_mints_when_compared_then_all_tokens_unique() -> None:
	# given
	tokens = DeviceStreamTokens()
	# when
	minted = {tokens.mint(_grant()) for _ in range(200)}
	# then
	assert len(minted) == 200


def test_given_minted_token_when_resolve_then_its_own_grant() -> None:
	# given
	tokens = DeviceStreamTokens()
	first = tokens.mint(_grant("a.mp4"))
	second = tokens.mint(_grant("b.mp4"))
	# when
	resolved = (tokens.resolve(first), tokens.resolve(second))
	# then
	assert resolved == (_grant("a.mp4"), _grant("b.mp4"))


def test_given_unknown_token_when_resolve_then_none() -> None:
	# given
	tokens = DeviceStreamTokens()
	# when
	resolved = tokens.resolve("nope")
	# then
	assert resolved is None


def test_given_revoked_token_when_resolve_then_none_and_other_tokens_unaffected() -> None:
	# given
	tokens = DeviceStreamTokens()
	revoked = tokens.mint(_grant("a.mp4"))
	kept = tokens.mint(_grant("b.mp4"))
	# when
	tokens.revoke(revoked)
	# then
	assert tokens.resolve(revoked) is None
	assert tokens.resolve(kept) == _grant("b.mp4")


def test_given_unknown_or_already_revoked_token_when_revoke_then_ignored() -> None:
	# given
	tokens = DeviceStreamTokens()
	token = tokens.mint(_grant())
	tokens.revoke(token)
	# when
	tokens.revoke(token)
	tokens.revoke("never-minted")
	# then
	assert tokens.resolve(token) is None
