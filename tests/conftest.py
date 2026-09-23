from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolated_managed_tools_dir(tmp_path, monkeypatch):
	tools = tmp_path / "managed-tools"
	tools.mkdir()
	monkeypatch.setenv("SPACEMAKER_TOOLS_DIR", str(tools))
