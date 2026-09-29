"""Guards against the web shell regressing to loose/untyped TypeScript.

`web/src/*.ts` is strict-mode TypeScript with no `// @ts-nocheck` escape hatches,
no `R.`-registry indirection (every call site imports the function it needs
directly), and relative imports that name the real `.ts` source file (see
`web/tsconfig.json`'s `rewriteRelativeImportExtensions`). See
`docs/agent-tooling.md` and `docs/ARCHITECTURE.md` for the conventions this
guards.
"""

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_SRC_DIR = REPO_ROOT / "web" / "src"
TS_FILES = sorted(WEB_SRC_DIR.glob("*.ts"))

TS_IGNORE_DIRECTIVE_RE = re.compile(r"@ts-nocheck|@ts-ignore")
RELATIVE_JS_IMPORT_RE = re.compile(r"""from\s+["']\.\.?/[^"']*\.js["']""")
REGISTRY_USAGE_RE = re.compile(r"\bR\.\w")
BARE_VAR_RE = re.compile(r"(?<![.\w$])\bvar\s+\w")


def test_given_web_src_dir_when_listing_ts_files_then_at_least_one_exists():
	# given / when
	files = TS_FILES

	# then
	assert files, f"expected at least one .ts file under {WEB_SRC_DIR}"


def test_given_a_web_src_ts_file_when_scanning_then_it_has_no_ts_ignore_directive():
	# given
	files = TS_FILES

	# when / then
	for path in files:
		text = path.read_text(encoding="utf-8")
		assert not TS_IGNORE_DIRECTIVE_RE.search(text), (
			f"{path.relative_to(REPO_ROOT)} bypasses strict type-checking with @ts-nocheck/@ts-ignore"
		)


def test_given_a_web_src_ts_file_when_scanning_imports_then_none_use_a_relative_js_extension():
	# given
	files = TS_FILES

	# when / then
	for path in files:
		text = path.read_text(encoding="utf-8")
		assert not RELATIVE_JS_IMPORT_RE.search(text), (
			f"{path.relative_to(REPO_ROOT)} imports a relative './x.js' module; "
			"use './x.ts' (rewriteRelativeImportExtensions rewrites it to .js at build time)"
		)


def test_given_a_web_src_ts_file_when_scanning_then_it_does_not_use_the_r_registry():
	# given
	files = TS_FILES

	# when / then
	for path in files:
		text = path.read_text(encoding="utf-8")
		assert not REGISTRY_USAGE_RE.search(text), (
			f"{path.relative_to(REPO_ROOT)} calls through the removed `R.` runtime registry; "
			"import the function directly from its defining module instead"
		)


def test_given_a_web_src_ts_file_when_scanning_then_it_declares_no_bare_var():
	# given
	files = TS_FILES

	# when / then
	for path in files:
		text = path.read_text(encoding="utf-8")
		assert not BARE_VAR_RE.search(text), (
			f"{path.relative_to(REPO_ROOT)} declares a variable with `var`; use `const`/`let`"
		)
