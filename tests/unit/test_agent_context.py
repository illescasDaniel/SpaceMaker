"""Guards against Cursor/Claude Code agent-context drift and re-bloat.

AGENTS.md is the sole always-on instructions file for both agents; anything
that should load only for a specific area lives as a hand-maintained rule
pair (`.cursor/rules/<name>.mdc` <-> `.claude/rules/<name>.md`). See
`docs/agent-tooling.md` "Rules — Cursor vs Claude Code".
"""

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
CURSOR_RULES_DIR = REPO_ROOT / ".cursor" / "rules"
CLAUDE_RULES_DIR = REPO_ROOT / ".claude" / "rules"
AGENTS_MD = REPO_ROOT / "AGENTS.md"
AGENTS_MD_LINE_BUDGET = 130

# Paths whose presence in tracked context files signals a stale reference to
# something this refactor deleted.
STALE_REFERENCE_SUBSTRINGS = (
	".cursor/rules/agent-memory.mdc",
	".cursor/rules/sdd.mdc",
	".cursor/rules/playbooks.mdc",
	".cursor/rules/graphrag-tools.mdc",
	".claude/rules/agent-memory.md",
	".claude/rules/sdd.md",
	".claude/rules/playbooks.md",
	".claude/rules/graphrag-tools.md",
	".cursor/skills/playbooks",
	".cursor/skills/hexagonal-python",
)
CONTEXT_FILES_TO_SCAN = (
	AGENTS_MD,
	REPO_ROOT / "memory" / "README.md",
	*CURSOR_RULES_DIR.glob("*.mdc"),
	*CLAUDE_RULES_DIR.glob("*.md"),
	*(REPO_ROOT / "docs").glob("*.md"),
	*(REPO_ROOT / "docs" / "playbooks").glob("*.md"),
)


def _split_frontmatter(text: str) -> tuple[dict, str]:
	"""Split a `---`-delimited YAML frontmatter block from the body below it."""
	assert text.startswith("---\n"), "expected a rule file to start with YAML frontmatter"
	_, frontmatter_raw, body = text.split("---\n", 2)
	return yaml.safe_load(frontmatter_raw) or {}, body


def _rule_pairs() -> list[tuple[Path, Path]]:
	cursor_rules = sorted(CURSOR_RULES_DIR.glob("*.mdc"))
	return [(path, CLAUDE_RULES_DIR / f"{path.stem}.md") for path in cursor_rules]


def test_given_cursor_rules_dir_when_listing_pairs_then_every_cursor_rule_has_a_claude_counterpart():
	# given
	pairs = _rule_pairs()

	# when / then
	assert pairs, "expected at least one Cursor rule to exist"
	for cursor_path, claude_path in pairs:
		assert claude_path.exists(), f"missing Claude Code counterpart for {cursor_path.name}"


def test_given_claude_rules_dir_when_listing_then_every_claude_rule_has_a_cursor_counterpart():
	# given
	claude_rules = sorted(CLAUDE_RULES_DIR.glob("*.md"))
	cursor_stems = {path.stem for path in CURSOR_RULES_DIR.glob("*.mdc")}

	# when / then
	assert claude_rules, "expected at least one Claude Code rule to exist"
	for claude_path in claude_rules:
		assert claude_path.stem in cursor_stems, (
			f"orphaned Claude Code rule with no Cursor counterpart: {claude_path.name}"
		)


def test_given_a_rule_pair_when_comparing_bodies_then_they_are_byte_identical():
	# given
	pairs = _rule_pairs()

	# when / then
	for cursor_path, claude_path in pairs:
		_, cursor_body = _split_frontmatter(cursor_path.read_text(encoding="utf-8"))
		_, claude_body = _split_frontmatter(claude_path.read_text(encoding="utf-8"))

		assert cursor_body == claude_body, f"rule body drifted between {cursor_path} and {claude_path}"


def test_given_a_rule_pair_when_comparing_scoping_then_always_apply_and_globs_are_equivalent():
	# given
	pairs = _rule_pairs()

	# when / then
	for cursor_path, claude_path in pairs:
		cursor_meta, _ = _split_frontmatter(cursor_path.read_text(encoding="utf-8"))
		claude_meta, _ = _split_frontmatter(claude_path.read_text(encoding="utf-8"))

		always_apply = cursor_meta.get("alwaysApply", False)
		globs = cursor_meta.get("globs")
		claude_paths = claude_meta.get("paths")

		if always_apply:
			assert globs is None, f"{cursor_path.name}: alwaysApply rules must not set globs"
			assert claude_paths is None, f"{claude_path.name}: always-on Claude rule must not set paths"
		else:
			assert globs is not None, f"{cursor_path.name}: alwaysApply: false requires globs"
			expected_paths = [globs] if isinstance(globs, str) else list(globs)
			assert claude_paths == expected_paths, (
				f"scoping mismatch between {cursor_path.name} (globs={globs!r}) "
				f"and {claude_path.name} (paths={claude_paths!r})"
			)


def test_given_cursor_rules_when_checking_frontmatter_then_no_unsupported_rule_kind_is_used():
	# given
	# Claude Code has no equivalent for Cursor's description-only "agent
	# requested" rules or manual (no globs, no alwaysApply) rules, so only
	# always-on or glob-scoped rules are allowed in this repo.
	pairs = _rule_pairs()

	# when / then
	for cursor_path, _ in pairs:
		meta, _ = _split_frontmatter(cursor_path.read_text(encoding="utf-8"))
		always_apply = meta.get("alwaysApply", False)
		globs = meta.get("globs")

		assert always_apply or globs, (
			f"{cursor_path.name}: must be alwaysApply or have globs (no agent-requested/manual rules)"
		)


def test_given_agents_md_when_counting_lines_then_it_stays_under_the_budget():
	# given
	line_count = len(AGENTS_MD.read_text(encoding="utf-8").splitlines())

	# when / then
	assert line_count <= AGENTS_MD_LINE_BUDGET, (
		f"AGENTS.md is {line_count} lines (budget {AGENTS_MD_LINE_BUDGET}) — "
		"move detail out to a skill or docs/agent-tooling.md instead of growing it in place"
	)


def test_given_tracked_context_files_when_scanning_then_no_stale_reference_to_deleted_rules_or_skills():
	# given
	offenders = []
	for path in CONTEXT_FILES_TO_SCAN:
		text = path.read_text(encoding="utf-8")
		for needle in STALE_REFERENCE_SUBSTRINGS:
			if needle in text:
				offenders.append(f"{path.relative_to(REPO_ROOT)} references deleted {needle}")

	# when / then
	assert not offenders, "\n".join(offenders)
