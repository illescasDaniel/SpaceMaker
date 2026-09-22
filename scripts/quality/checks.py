#!/usr/bin/env python3
"""Dispatch quality gate to checks.sh (Unix)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
	parser = argparse.ArgumentParser(description="SpaceMaker quality gate")
	parser.add_argument("--fix", action="store_true")
	parser.add_argument("--quiet", action="store_true")
	parser.add_argument("--skip-web", action="store_true")
	args, rest = parser.parse_known_args(argv)
	script = _REPO / "scripts" / "quality" / "checks.sh"
	cmd = [str(script)]
	if args.fix:
		cmd.append("--fix")
	if args.quiet:
		cmd.append("--quiet")
	if args.skip_web:
		cmd.append("--skip-web")
	cmd.extend(rest)
	return subprocess.call(cmd, cwd=_REPO)


if __name__ == "__main__":
	sys.exit(main())
