from __future__ import annotations

from pathlib import Path

import pytest

from spacemaker.adapters.outbound.host import open_paths


def test_given_directory_when_reveal_in_file_manager_on_linux_then_xdg_opens_that_directory(
	monkeypatch: pytest.MonkeyPatch,
	tmp_path: Path,
) -> None:
	# given
	folder = tmp_path / "SpaceMaker"
	folder.mkdir()
	calls: list[list[str]] = []

	def fake_run(cmd: list[str], *, check: bool) -> None:
		_ = check
		calls.append(cmd)

	monkeypatch.setattr(open_paths.sys, "platform", "linux")
	monkeypatch.setattr(open_paths.subprocess, "run", fake_run)

	# when
	open_paths.reveal_in_file_manager(str(folder))

	# then
	assert calls == [["xdg-open", str(folder.resolve())]]


def test_given_file_when_reveal_in_file_manager_on_linux_then_xdg_opens_parent_directory(
	monkeypatch: pytest.MonkeyPatch,
	tmp_path: Path,
) -> None:
	# given
	file_path = tmp_path / "note.txt"
	file_path.write_text("x", encoding="utf-8")
	calls: list[list[str]] = []

	def fake_run(cmd: list[str], *, check: bool) -> None:
		_ = check
		calls.append(cmd)

	monkeypatch.setattr(open_paths.sys, "platform", "linux")
	monkeypatch.setattr(open_paths.subprocess, "run", fake_run)

	# when
	open_paths.reveal_in_file_manager(str(file_path))

	# then
	assert calls == [["xdg-open", str(tmp_path.resolve())]]
