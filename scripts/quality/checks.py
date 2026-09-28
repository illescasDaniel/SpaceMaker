#!/usr/bin/env python3
"""Quality gate: ruff, ty, pytest, and web (Biome + tsc).

Runs natively via ``uv`` / ``npm`` so Windows PowerShell does not need a working
``bash`` on ``PATH`` (the WindowsApps WSL stub often shadows Git Bash and fails
with “no installed distributions”).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


_REPO = Path(__file__).resolve().parents[2]
_PYTEST_TARGETS = [
	"tests/unit",
	"tests/integration",
	"mcp-servers/mcp-nav-shared/tests",
	"mcp-servers/codenav_mcp/tests",
	"mcp-servers/webnav_mcp/tests",
]


def _log(quiet: bool, message: str) -> None:
	if not quiet:
		print(message)


def _run(cmd: list[str], *, quiet: bool) -> int:
	del quiet  # reserved for future capture/log suppression
	return subprocess.call(cmd, cwd=_REPO)


def _uv(*args: str) -> list[str]:
	return ["uv", "run", *args]


def _npm() -> str | None:
	return shutil.which("npm")


def step_ruff(*, fix: bool, quiet: bool) -> int:
	_log(quiet, "== ruff ==")
	targets = ["src", "tests"]
	if fix:
		code = _run(_uv("ruff", "check", *targets, "--fix"), quiet=quiet)
		if code != 0:
			return code
		return _run(_uv("ruff", "format", *targets), quiet=quiet)
	code = _run(_uv("ruff", "check", *targets), quiet=quiet)
	if code != 0:
		return code
	return _run(_uv("ruff", "format", "--check", *targets), quiet=quiet)


def step_ty(*, quiet: bool) -> int:
	_log(quiet, "== ty ==")
	return _run(_uv("ty", "check"), quiet=quiet)


def step_pytest(*, quiet: bool, extra: list[str]) -> int:
	_log(quiet, "== pytest ==")
	cmd = _uv("pytest", *_PYTEST_TARGETS, "-q", *extra)
	return _run(cmd, quiet=quiet)


def step_web(*, fix: bool, quiet: bool) -> int:
	_log(quiet, "== web ==")
	if not (_REPO / "package.json").is_file():
		print("skip web: no package.json", file=sys.stderr)
		return 0
	npm = _npm()
	if npm is None:
		print("skip web: npm not installed (run npm ci when Node is available)", file=sys.stderr)
		return 0
	if not (_REPO / "node_modules" / "@biomejs" / "biome").is_dir():
		print("Missing node_modules. Run: npm ci", file=sys.stderr)
		return 1
	script = "format" if fix else "check"
	return _run([npm, "run", script], quiet=quiet)


def main(argv: list[str] | None = None) -> int:
	parser = argparse.ArgumentParser(description="SpaceMaker quality gate")
	parser.add_argument("--fix", action="store_true")
	parser.add_argument("--quiet", action="store_true")
	parser.add_argument("--skip-web", action="store_true")
	args, rest = parser.parse_known_args(argv)

	if not (_REPO / ".venv").is_dir():
		print("Missing .venv. Run: uv run task sync-dev", file=sys.stderr)
		return 1

	fail = 0
	if step_ruff(fix=args.fix, quiet=args.quiet) != 0:
		print("fail: ruff", file=sys.stderr)
		fail = 1
	else:
		_log(args.quiet, "ok: ruff")

	if step_ty(quiet=args.quiet) != 0:
		print("fail: ty", file=sys.stderr)
		fail = 1
	else:
		_log(args.quiet, "ok: ty")

	if step_pytest(quiet=args.quiet, extra=rest) != 0:
		print("fail: pytest", file=sys.stderr)
		fail = 1
	else:
		_log(args.quiet, "ok: pytest")

	if not args.skip_web:
		if step_web(fix=args.fix, quiet=args.quiet) != 0:
			print("fail: web", file=sys.stderr)
			fail = 1
		else:
			_log(args.quiet, "ok: web")

	return fail


if __name__ == "__main__":
	sys.exit(main())
