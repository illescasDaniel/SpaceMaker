"""Tests for the code-grader's mechanical pre-checks (scripts/quality/grade_prechecks.py)."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "quality" / "grade_prechecks.py"
_spec = importlib.util.spec_from_file_location("grade_prechecks", _SCRIPT)
assert _spec is not None and _spec.loader is not None
gp = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = gp
_spec.loader.exec_module(gp)

GOOD_SPEC = """# Feature

## Metadata

- **Wireframe:** [wireframes/app.html](../../wireframes/app.html)

## Design decisions

| Decision | Answer |
|---|---|
| Success criteria | No file is lost and re-running is idempotent |
| Failure handling | Bad files move to invalid/ and the user sees a banner |
| Performance & resource budget | N/A — no heavy work happens in this feature |
| Trust boundary | Upload filenames are validated at the inbound adapter |

## Acceptance criteria (BDD)

### Scenario: It works

- **Given** a thing
- **When** it runs
- **Then** it works

## Out of scope

- Nothing
"""


def _write(root: Path, rel: str, text: str) -> Path:
	path = root / rel
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(text, encoding="utf-8")
	return path


def _git_repo(root: Path) -> None:
	for args in (["init", "-q", "-b", "main"], ["config", "user.email", "t@t"], ["config", "user.name", "t"]):
		subprocess.run(["git", *args], cwd=root, check=True)  # noqa: S607


def _commit_all(root: Path) -> None:
	subprocess.run(["git", "add", "-A"], cwd=root, check=True)  # noqa: S607
	subprocess.run(["git", "commit", "-qm", "x"], cwd=root, check=True)  # noqa: S607


def test_given_core_file_importing_fastapi_and_touched_when_checking_layering_then_it_fails(tmp_path):
	# given
	_write(tmp_path, "src/spacemaker/application/use_case.py", "import fastapi\n")
	report = gp.Report()
	added = {"src/spacemaker/application/use_case.py": {1}}

	# when
	gp.check_layering(tmp_path, added, report)

	# then
	assert report.fails == 1
	assert "use_case.py:1 imports fastapi" in "\n".join(report.lines)


def test_given_untouched_legacy_violation_when_checking_layering_then_it_only_warns(tmp_path):
	# given
	_write(tmp_path, "src/spacemaker/application/legacy.py", "from spacemaker.bootstrap.paths import x\n")
	report = gp.Report()

	# when
	gp.check_layering(tmp_path, {}, report)

	# then
	assert report.fails == 0
	assert any(line.startswith("WARN") for line in report.lines)


def test_given_clean_core_when_checking_layering_then_it_passes(tmp_path):
	# given
	_write(tmp_path, "src/spacemaker/domain/entity.py", "from dataclasses import dataclass\n")
	report = gp.Report()

	# when
	gp.check_layering(tmp_path, {"src/spacemaker/domain/entity.py": {1}}, report)

	# then
	assert report.fails == 0
	assert report.lines[0].startswith("PASS")


def test_given_complete_spec_when_checking_then_no_failures(tmp_path):
	# given
	_write(tmp_path, "wireframes/app.html", "<html></html>")
	spec = _write(tmp_path, "specs/f/SPEC.md", GOOD_SPEC)
	report = gp.Report()

	# when
	gp.check_spec(tmp_path, spec, report)

	# then
	assert report.fails == 0, report.lines


def test_given_spec_without_design_decisions_when_checking_then_it_fails(tmp_path):
	# given
	_write(tmp_path, "wireframes/app.html", "<html></html>")
	text = GOOD_SPEC.replace("## Design decisions", "## Notes")
	spec = _write(tmp_path, "specs/f/SPEC.md", text)
	report = gp.Report()

	# when
	gp.check_spec(tmp_path, spec, report)

	# then
	assert any("missing ## Design decisions" in line for line in report.lines)


def test_given_scenario_without_then_when_checking_spec_then_it_fails(tmp_path):
	# given
	_write(tmp_path, "wireframes/app.html", "<html></html>")
	spec = _write(tmp_path, "specs/f/SPEC.md", GOOD_SPEC.replace("- **Then** it works\n", ""))
	report = gp.Report()

	# when
	gp.check_spec(tmp_path, spec, report)

	# then
	assert any("lack Given/When/Then" in line for line in report.lines)


def test_given_missing_wireframe_file_when_checking_spec_then_it_fails(tmp_path):
	# given
	spec = _write(tmp_path, "specs/f/SPEC.md", GOOD_SPEC)
	report = gp.Report()

	# when
	gp.check_spec(tmp_path, spec, report)

	# then
	assert any("wireframe(s) not found" in line for line in report.lines)


@pytest.mark.parametrize(
	"row",
	[
		"| Failure handling | |",
		"| Failure handling | N/A |",
	],
)
def test_given_empty_or_bare_na_decision_when_checking_then_it_is_reported(row):
	# given
	section = "\n".join(
		[
			"| Success criteria | No file is lost and re-running is idempotent |",
			row,
			"| Performance & resource budget | Under two seconds on a mid laptop |",
			"| Trust boundary | Filenames validated at the inbound adapter |",
		]
	)

	# when
	problems = gp._design_decision_problems(section)

	# then
	assert problems == ["'failure handling' empty or bare N/A"]


def test_given_new_tests_on_branch_when_checking_then_bad_names_fail_and_missing_markers_warn(tmp_path):
	# given
	_git_repo(tmp_path)
	_write(tmp_path, "README.md", "x")
	_commit_all(tmp_path)
	_write(
		tmp_path,
		"tests/unit/test_new.py",
		"def test_given_a_when_b_then_c():\n\t# given\n\t# when\n\t# then\n\tpass\n\n\ndef test_it_works():\n\tpass\n",
	)
	report = gp.Report()

	# when
	added = gp.added_lines_by_file(tmp_path, "main")
	gp.check_new_tests(tmp_path, added, report)

	# then
	assert report.fails == 1
	text = "\n".join(report.lines)
	assert "test_it_works" in text
	assert "lack # given" in text


def test_given_test_edited_but_function_untouched_when_checking_then_it_is_ignored(tmp_path):
	# given
	_git_repo(tmp_path)
	old = "def test_legacy_name():\n\tpass\n\n\n# trailing\n"
	_write(tmp_path, "tests/unit/test_old.py", old)
	_commit_all(tmp_path)
	_write(tmp_path, "tests/unit/test_old.py", old + "# another comment\n")
	report = gp.Report()

	# when
	added = gp.added_lines_by_file(tmp_path, "main")
	gp.check_new_tests(tmp_path, added, report)

	# then
	assert report.fails == 0
