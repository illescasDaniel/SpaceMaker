# LAN access and file transfer
Updated: 2026-11-17. What phones on the network can reach, the passcode, and the send/receive/transfer flows.

## Now
Non-loopback peers reach only an allow-list ([lan-access-default-deny-allowlist](../notes/lan-access-default-deny-allowlist.md)) behind an optional passcode that is access control, not encryption ([network-passcode-access-control](../notes/network-passcode-access-control.md)). Wi-Fi upload with a session token is the default extract ([wifi-extract-default](../notes/wifi-extract-default.md)).

## How it got here
- 2026-09-23 control APIs loopback-only, everything else open on LAN ([note](../notes/lan-loopback-control-plane.md)); reversed to default-deny on 2026-10-19 ([note](../notes/lan-access-default-deny-allowlist.md)).

## Notes
- [LAN access: default-deny allow-list keyed on the TCP peer](../notes/lan-access-default-deny-allowlist.md) 2026-10-19: non-loopback peers reach only an allow-list (403 desktop-only otherwise); shell chosen by TCP peer, not Host
- [Network passcode is access control, not AES encryption](../notes/network-passcode-access-control.md) 2026-10-02: scrypt passcode + HMAC cookie, not AES: plain-http LAN pages have no WebCrypto; record in its own 0600 file
- [Transfer desktop Download saves to Documents/SpaceMaker; Home centered + 960×720](../notes/transfer-download-to-documents-window.md) 2026-09-27: desktop Transfer Download saves to Documents/SpaceMaker; Home centered, window 960x720
- [Transfer files: ephemeral staging + SHA-256 name collision; fifth Home module](../notes/transfer-files-ephemeral-staging.md) 2026-09-25: Transfer files stage bytes in an ephemeral root; SHA-256 dedupes same-name items
- [Send files: folder zips and stable LAN share token](../notes/send-files-folder-zips-share-token.md) 2026-09-23: folders shared as on-demand zips; one share token reused until Clear/Home/quit
- [Wi‑Fi extract as default (tokenized LAN upload)](../notes/wifi-extract-default.md) 2026-09-22: Wi-Fi phone upload with a session token is the default extract method
- [LAN firewall probe in bootstrap](../notes/lan-firewall-probe.md) 2026-09-22: firewalld/UFW probe and LAN self-test exposed in server-info

## History (superseded)
- [LAN server: loopback-only desktop control plane](../notes/lan-loopback-control-plane.md) 2026-09-23 → superseded by lan-access-default-deny-allowlist
