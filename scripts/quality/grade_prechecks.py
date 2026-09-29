#!/usr/bin/env python3
"""Mechanical pre-checks for the code-grader agent (SDD Phase 5).

Deterministic, fast checks the grader would otherwise have to eyeball: hexagonal
import boundaries, test naming/structure for tests added on this branch, and the
structure of the SPEC.md being graded. Judgement calls (does the code actually
satisfy the scenario? is the test meaningful?) stay with the grader.

Exit code 1 when any hard ``FAIL`` is found. ``WARN`` lines are advisory and
never change the exit code. Scenario-to-test coverage is deliberately not
checked here: test names are freeform, so name matching was too noisy to trust.

    uv run python scripts/quality/grade_prechecks.py --spec specs/<feature>/SPEC.md
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


_REPO = Path(__file__).resolve().parents[2]

CORE_DIRS = ("domain", "ports", "application")
# Top-level module names / dotted prefixes the core must never import (see hexagonal-python rule).
FORBIDDEN_CORE_IMPORTS = (
	"fastapi",
	"starlette",
	"uvicorn",
	"webview",
	"subprocess",
	"spacemaker.adapters",
	"spacemaker.bootstrap",
	"spacemaker.desktop",
)
DESIGN_DECISION_KEYS = ("success criteria", "failure handling", "performance", "trust boundary")
TEST_NAME_RE = re.compile(r"^test_given_.+_when_.+_then_.+")


@dataclass
class Report:
	"""Accumulates check results; ``fails`` decide the exit code."""

	lines: list[str] = field(default_factory=list)
	fails: int = 0

	def ok(self, message: str) -> None:
		self.lines.append(f"PASS  {message}")

	def fail(self, message: str) -> None:
		self.fails += 1
		self.lines.append(f"FAIL  {message}")

	def warn(self, message: str) -> None:
		self.lines.append(f"WARN  {message}")


def _git(repo: Path, *args: str) -> str:
	result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)  # noqa: S603, S607
	return result.stdout


def added_lines_by_file(repo: Path, base: str) -> dict[str, set[int]]:
	"""Map each file changed vs ``base`` (committed, staged, or untracked) to its added line numbers."""
	merge_base = _git(repo, "merge-base", base, "HEAD").strip() or base
	diff = _git(repo, "diff", "--unified=0", merge_base)
	added: dict[str, set[int]] = {}
	current: str | None = None
	for raw in diff.splitlines():
		if raw.startswith("+++ b/"):
			current = raw[6:]
			added.setdefault(current, set())
		elif raw.startswith("@@") and current is not None:
			match = re.search(r"\+(\d+)(?:,(\d+))?", raw)
			if match:
				start, count = int(match.group(1)), int(match.group(2) or 1)
				added[current].update(range(start, start + count))
	for name in _git(repo, "ls-files", "--others", "--exclude-standard").splitlines():
		path = repo / name
		if path.is_file():
			added[name] = set(range(1, len(path.read_text(encoding="utf-8", errors="replace").splitlines()) + 1))
	return added


def _imported_modules(tree: ast.AST) -> list[tuple[int, str]]:
	found: list[tuple[int, str]] = []
	for node in ast.walk(tree):
		if isinstance(node, ast.Import):
			found.extend((node.lineno, alias.name) for alias in node.names)
		elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
			found.append((node.lineno, node.module))
	return found


def check_layering(repo: Path, added: dict[str, set[int]], report: Report) -> None:
	"""Core layers (domain/ports/application) must not import frameworks or adapters.

	Only files touched on this branch hard-fail; violations in untouched legacy files are warnings.
	"""
	package = repo / "src" / "spacemaker"
	violations: list[str] = []
	legacy: list[str] = []
	scanned = 0
	for layer in CORE_DIRS:
		for path in sorted((package / layer).rglob("*.py")):
			scanned += 1
			tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
			for lineno, module in _imported_modules(tree):
				for forbidden in FORBIDDEN_CORE_IMPORTS:
					if module == forbidden or module.startswith(f"{forbidden}."):
						rel = path.relative_to(repo).as_posix()
						(violations if rel in added else legacy).append(f"{rel}:{lineno} imports {module}")
	if legacy:
		report.warn(f"hexagonal layering: {len(legacy)} pre-existing forbidden import(s) in untouched core files")
		report.lines.extend(f"        {v}" for v in legacy)
	if violations:
		report.fail(f"hexagonal layering: {len(violations)} forbidden import(s) in core")
		report.lines.extend(f"        {v}" for v in violations)
	else:
		report.ok(
			f"hexagonal layering: no forbidden imports in files changed on this branch ({scanned} core file(s) scanned)"
		)


def _has_markers(body: str) -> bool:
	"""``# given`` plus either separate ``# when`` / ``# then`` or the repo's combined ``# when / then``."""
	return "# given" in body and ("# when / then" in body or ("# when" in body and "# then" in body))


def check_new_tests(repo: Path, added: dict[str, set[int]], report: Report) -> None:
	"""Naming (hard) and given/when/then comments (advisory) for test functions added on this branch."""
	new_names: list[str] = []
	bad_names: list[str] = []
	missing_markers: list[str] = []
	for name, lines in sorted(added.items()):
		if not (name.startswith("tests/") and name.endswith(".py") and Path(name).name.startswith("test_")):
			continue
		path = repo / name
		if not path.is_file():
			continue
		source = path.read_text(encoding="utf-8")
		source_lines = source.splitlines()
		for node in ast.walk(ast.parse(source)):
			if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) or not node.name.startswith("test_"):
				continue
			if node.lineno not in lines:
				continue
			new_names.append(node.name)
			if not TEST_NAME_RE.match(node.name):
				bad_names.append(f"{name}:{node.lineno} {node.name}")
			body = "\n".join(source_lines[node.lineno - 1 : node.end_lineno])
			if not _has_markers(body):
				missing_markers.append(f"{name}:{node.lineno} {node.name}")
	if not new_names:
		report.warn("tests: no new test functions found on this branch")
		return
	if bad_names:
		report.fail(f"test naming: {len(bad_names)} of {len(new_names)} new test(s) not test_given_…_when_…_then_…")
		report.lines.extend(f"        {b}" for b in bad_names)
	else:
		report.ok(f"test naming: {len(new_names)} new test(s) follow given/when/then")
	if missing_markers:
		report.warn(f"tests: {len(missing_markers)} new test(s) lack # given / # when / # then comments")
		report.lines.extend(f"        {m}" for m in missing_markers)


def _section(text: str, heading: str) -> str | None:
	match = re.search(
		rf"^##\s+{re.escape(heading)}\b.*?$(.*?)(?=^##\s|\Z)", text, re.MULTILINE | re.DOTALL | re.IGNORECASE
	)
	return match.group(1) if match else None


def _design_decision_problems(section: str) -> list[str]:
	"""Each decision must appear and carry real content; a bare ``N/A`` needs a reason."""
	lines = section.lower().splitlines()
	starts = {key: next((i for i, line in enumerate(lines) if key in line), None) for key in DESIGN_DECISION_KEYS}
	ordered = sorted(i for i in starts.values() if i is not None)
	problems = []
	for key, start in starts.items():
		if start is None:
			problems.append(f"'{key}' missing")
			continue
		end = next((i for i in ordered if i > start), len(lines))
		chunk = " ".join(lines[start:end])
		content = re.sub(r"[^a-z0-9]+", "", chunk.split(key, 1)[1])
		if len(content) < 15 or ("n/a" in chunk and len(content.replace("na", "", 1)) < 12):
			problems.append(f"'{key}' empty or bare N/A")
	return problems


def check_spec(repo: Path, spec: Path, report: Report) -> None:
	"""Structure of the SPEC.md under review."""
	rel = spec.relative_to(repo) if spec.is_absolute() else spec
	text = (repo / rel).read_text(encoding="utf-8")

	metadata = _section(text, "Metadata")
	if metadata is None:
		report.fail(f"{rel}: missing ## Metadata")
	else:
		wireframes = re.findall(r"wireframes/[\w./#-]+\.html", metadata)
		missing = [w for w in wireframes if not (repo / w).is_file()]
		if not wireframes:
			report.warn(f"{rel}: Metadata links no wireframes/*.html")
		elif missing:
			report.fail(f"{rel}: linked wireframe(s) not found: {', '.join(missing)}")
		else:
			report.ok(f"{rel}: linked wireframe(s) exist")

	decisions = _section(text, "Design decisions")
	if decisions is None:
		report.fail(
			f"{rel}: missing ## Design decisions (success criteria, failure handling, performance, trust boundary)"
		)
	else:
		problems = _design_decision_problems(decisions)
		if problems:
			report.fail(f"{rel}: Design decisions incomplete: {'; '.join(problems)}")
		else:
			report.ok(f"{rel}: all four design decisions answered")

	if _section(text, "Out of scope") is None:
		report.warn(f"{rel}: missing ## Out of scope")

	scenarios = re.findall(r"^###\s+Scenario:\s*(.+?)\s*$", text, re.MULTILINE)
	if not scenarios:
		report.fail(f"{rel}: no '### Scenario:' headings found")
		return
	incomplete = []
	for block in re.split(r"^###\s+Scenario:", text, flags=re.MULTILINE)[1:]:
		title = block.splitlines()[0].strip()
		if not all(re.search(rf"\*\*{kw}\*\*", block) for kw in ("Given", "When", "Then")):
			incomplete.append(title)
	if incomplete:
		report.fail(f"{rel}: {len(incomplete)} scenario(s) lack Given/When/Then")
		report.lines.extend(f"        {t}" for t in incomplete)
	else:
		report.ok(f"{rel}: {len(scenarios)} scenario(s), each with Given/When/Then")


def run(repo: Path, specs: list[Path], base: str) -> Report:
	report = Report()
	added = added_lines_by_file(repo, base)
	check_layering(repo, added, report)
	check_new_tests(repo, added, report)
	for spec in specs:
		check_spec(repo, spec, report)
	return report


def main(argv: list[str] | None = None) -> int:
	parser = argparse.ArgumentParser(description="Mechanical pre-checks for the code grader")
	parser.add_argument("--spec", action="append", default=[], type=Path, help="SPEC.md to check (repeatable)")
	parser.add_argument("--base", default="main", help="git base ref for 'added on this branch' (default: main)")
	args = parser.parse_args(argv)

	report = run(_REPO, args.spec, args.base)
	print("\n".join(report.lines))
	print(f"\n{'FAILED' if report.fails else 'OK'}: {report.fails} hard failure(s)")
	return 1 if report.fails else 0


if __name__ == "__main__":
	sys.exit(main())
