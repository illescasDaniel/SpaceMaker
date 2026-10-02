from __future__ import annotations

from pathlib import Path

from spacemaker.adapters.outbound.filesystem.local import LocalFileSystem


def test_given_identical_and_different_files_when_compared_then_only_identical_match(tmp_path: Path) -> None:
	# given
	big = b"abc" * 800_000
	(tmp_path / "a").write_bytes(big)
	(tmp_path / "b").write_bytes(big)
	(tmp_path / "c").write_bytes(big[:-1] + b"X")
	fs = LocalFileSystem()
	# when / then
	assert fs.files_have_same_content(str(tmp_path / "a"), str(tmp_path / "b")) is True
	assert fs.files_have_same_content(str(tmp_path / "a"), str(tmp_path / "c")) is False
	assert fs.files_have_same_content(str(tmp_path / "a"), str(tmp_path / "missing")) is False
