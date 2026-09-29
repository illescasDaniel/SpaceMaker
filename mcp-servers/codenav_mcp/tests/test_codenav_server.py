"""Fast unit tests for `codenav_mcp.server` (no live language servers)."""

from __future__ import annotations

import pytest
from codenav_mcp import server as codenav_server
from codenav_mcp.server import _check_python_file, _protocol_class_names
from mcp_nav_shared.errors import ToolInputError, format_tool_error


def test_given_python_file_when_check_python_file_then_no_error():
	# given / when / then — .py and .pyi are both accepted, no exception raised
	_check_python_file("src/spacemaker/bootstrap/services.py")
	_check_python_file("src/spacemaker/stubs/foo.pyi")


def test_given_non_python_file_when_check_python_file_then_tool_input_error():
	# given — a non-Python file must be rejected before it ever reaches ty,
	# which would otherwise mis-parse it as Python (e.g. diagnostics on a
	# README producing a wall of bogus syntax errors)
	# when
	with pytest.raises(ToolInputError) as caught:
		_check_python_file("README.md")
	# then
	text = format_tool_error(caught.value)
	assert text == "codenav only supports Python files (.py/.pyi), got 'README.md'"


def test_given_plain_protocol_base_when_protocol_class_names_then_included():
	source = "from typing import Protocol\n\nclass Port(Protocol):\n\tdef run(self) -> None: ...\n"
	assert _protocol_class_names(source) == {"Port"}


def test_given_qualified_protocol_base_when_protocol_class_names_then_included():
	source = "import typing\n\nclass Port(typing.Protocol):\n\tdef run(self) -> None: ...\n"
	assert _protocol_class_names(source) == {"Port"}


def test_given_subscripted_protocol_base_when_protocol_class_names_then_included():
	source = "from typing import Protocol\nfrom typing import TypeVar\n\nT = TypeVar('T')\n\nclass Port(Protocol[T]):\n\tpass\n"
	assert _protocol_class_names(source) == {"Port"}


def test_given_non_protocol_class_when_protocol_class_names_then_excluded():
	source = "class AppServices:\n\tdef run(self) -> None: ...\n"
	assert _protocol_class_names(source) == set()


def test_given_nested_protocol_class_when_protocol_class_names_then_found_at_any_depth():
	source = "from typing import Protocol\n\nclass Outer:\n\tclass Inner(Protocol):\n\t\tdef run(self) -> None: ...\n"
	assert _protocol_class_names(source) == {"Inner"}


def test_given_no_source_root_env_when_module_loaded_then_source_root_defaults_to_workspace_root():
	# codenav_mcp.server reads CODENAV_MCP_SOURCE_ROOT once at import time; in
	# a plain test environment (no .mcp.json-injected env) it should fall back
	# to scanning/deriving import paths against the whole workspace, not a
	# hardcoded "src" layout.
	assert codenav_server.SOURCE_ROOT == codenav_server.WORKSPACE_ROOT


def test_given_unchanged_file_when_cached_protocol_names_twice_then_parses_once(tmp_path, monkeypatch):
	# given
	src = tmp_path / "port.py"
	src.write_text("from typing import Protocol\n\nclass P(Protocol):\n\tdef f(self) -> None: ...\n", encoding="utf-8")
	codenav_server._protocol_names_cache.clear()
	parsed: list[str] = []
	real = codenav_server._protocol_class_names
	monkeypatch.setattr(codenav_server, "_protocol_class_names", lambda text: parsed.append(text) or real(text))
	# when
	first = codenav_server._cached_protocol_class_names(src)
	second = codenav_server._cached_protocol_class_names(src)
	# then
	assert first == second == {"P"}
	assert len(parsed) == 1


def test_given_edited_file_when_cached_protocol_names_then_reparsed(tmp_path):
	# given
	src = tmp_path / "port.py"
	src.write_text("class P:\n\tpass\n", encoding="utf-8")
	codenav_server._protocol_names_cache.clear()
	assert codenav_server._cached_protocol_class_names(src) == set()
	# when
	src.write_text("from typing import Protocol\n\nclass P(Protocol):\n\tpass\n", encoding="utf-8")
	# then
	assert codenav_server._cached_protocol_class_names(src) == {"P"}


def test_given_edited_source_file_when_source_signature_then_differs(tmp_path):
	# given
	a = tmp_path / "a.py"
	a.write_text("x = 1\n", encoding="utf-8")
	before = codenav_server._source_signature([a])
	# when
	a.write_text("x = 12\n", encoding="utf-8")
	# then
	assert codenav_server._source_signature([a]) != before
