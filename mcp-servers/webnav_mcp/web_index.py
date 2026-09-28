"""Workspace-wide CSS custom-property and class/id selector index for webnav.

The CSS/HTML language servers each see one document at a time, so `var(--x)`
usages and `#id`/`.class` selectors can't be cross-referenced across files —
the most common question for this project's `--custom-properties` (defined
once in `theme.css`, used across every CSS file, inline `<style>` block and
wireframe). This is a pure-Python scanner, not a language server: no
`@import` resolution, no CSS parser, regex/brace-stack grade. It rescans on
every call rather than caching — about 20 files total, a few ms — so there is
no cache-invalidation story to get wrong.

Two roots are indexed separately (`static` = the production web assets,
`wireframes` = UX layout truth): they define their own values/markup, so
mixing them in one answer would be misleading. Positions are 1-indexed lines,
matching the rest of the MCP tools.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


STATIC_ROOT_REL = Path("src/spacemaker/adapters/inbound/web/static")
WIREFRAME_ROOT_REL = Path("wireframes")

_VAR_NAME_RE = re.compile(r"--[a-zA-Z0-9_-]+")
_VAR_DECL_RE = re.compile(r"(--[a-zA-Z0-9_-]+)\s*:\s*([^;{}]+);")
_VAR_USE_RE = re.compile(r"var\(\s*(--[a-zA-Z0-9_-]+)\s*(,)?")
_SELECTOR_TOKEN_RE = re.compile(r"[.#][a-zA-Z_-][a-zA-Z0-9_-]*")

_STYLE_BLOCK_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)
_STYLE_ATTR_RE = re.compile(r'\bstyle\s*=\s*"([^"]*)"', re.IGNORECASE)
_ID_ATTR_RE = re.compile(r'\bid\s*=\s*"([^"]+)"', re.IGNORECASE)
_CLASS_ATTR_RE = re.compile(r'\bclass\s*=\s*"([^"]*)"', re.IGNORECASE)

_JS_SETPROPERTY_RE = re.compile(r"\.setProperty\(\s*[\"'](--[a-zA-Z0-9_-]+)[\"']")
_JS_GETPROPERTYVALUE_RE = re.compile(r"\.getPropertyValue\(\s*[\"'](--[a-zA-Z0-9_-]+)[\"']")
_JS_GET_ELEMENT_BY_ID_RE = re.compile(r"getElementById\(\s*[\"']([^\"']*)[\"']\s*(\+)?")
_JS_CLASSLIST_RE = re.compile(r"classList\.(add|remove|toggle|contains)\(([^)]*)\)")
_JS_QUERY_RE = re.compile(r"querySelectorAll?\(\s*[\"']([^\"']*)[\"']")
_JS_CLASSNAME_ASSIGN_RE = re.compile(r"className\s*\+?=\s*[\"']([^\"']*)[\"']")
_STRING_LITERAL_RE = re.compile(r"[\"']([^\"']*)[\"']")


def _line_at(text: str, index: int) -> int:
	"""1-indexed line number for a character offset."""
	return text.count("\n", 0, index) + 1


def _strip_css_comments(text: str) -> str:
	return re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.DOTALL)


def _strip_js_comments(text: str) -> str:
	text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.DOTALL)
	return re.sub(r"//[^\n]*", "", text)


def _strip_html_comments(text: str) -> str:
	return re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.DOTALL)


@dataclass(frozen=True)
class VarDeclaration:
	name: str
	value: str
	context: str  # e.g. "@media (prefers-color-scheme: dark) › :root"
	file: str  # relative to the root
	line: int


@dataclass(frozen=True)
class VarUsage:
	name: str
	file: str
	line: int
	has_fallback: bool = False


@dataclass(frozen=True)
class SelectorHit:
	token: str  # "#id" or ".class"
	kind: str  # "css" | "html" | "js"
	file: str
	line: int
	detail: str = ""  # e.g. "getElementById", "classList.add", "CSS rule"
	dynamic: bool = False  # a JS hit built from string-concatenation (only a static prefix is known)


@dataclass
class RootIndex:
	name: str
	root: Path
	var_declarations: dict[str, list[VarDeclaration]] = field(default_factory=dict)
	var_usages: dict[str, list[VarUsage]] = field(default_factory=dict)
	selector_hits: dict[str, list[SelectorHit]] = field(default_factory=dict)

	def add_declaration(self, decl: VarDeclaration) -> None:
		self.var_declarations.setdefault(decl.name, []).append(decl)

	def add_usage(self, usage: VarUsage) -> None:
		self.var_usages.setdefault(usage.name, []).append(usage)

	def add_selector_hit(self, hit: SelectorHit) -> None:
		self.selector_hits.setdefault(hit.token, []).append(hit)


@dataclass
class _Block:
	selector: str
	start: int  # index just after the opening '{'
	end: int  # index of the matching '}' (-1 until closed)
	parent: _Block | None


def _parse_blocks(text: str) -> list[_Block]:
	"""Brace-stack pass over (comment-stripped) CSS: one `_Block` per `{...}`,
	each knowing its own selector text and parent — enough to build a context
	breadcrumb for anything nested inside it. Doesn't account for `{`/`}`
	inside CSS string values (none occur in this codebase)."""
	blocks: list[_Block] = []
	open_stack: list[_Block] = []
	buf_start = 0
	for i, ch in enumerate(text):
		if ch == "{":
			selector = re.sub(r"\s+", " ", text[buf_start:i]).strip()
			block = _Block(selector=selector, start=i + 1, end=-1, parent=open_stack[-1] if open_stack else None)
			open_stack.append(block)
			blocks.append(block)
			buf_start = i + 1
		elif ch == "}":
			if open_stack:
				open_stack.pop().end = i
			buf_start = i + 1
	return blocks


def _enclosing_block(blocks: list[_Block], idx: int) -> _Block | None:
	best: _Block | None = None
	for b in blocks:
		if b.end == -1:
			continue
		if b.start <= idx < b.end and (best is None or (b.end - b.start) < (best.end - best.start)):
			best = b
	return best


def _breadcrumb(block: _Block | None) -> str:
	parts: list[str] = []
	while block is not None:
		if block.selector:
			parts.append(block.selector)
		block = block.parent
	return " › ".join(reversed(parts))


def _scan_css_text(text: str, file_rel: str, root_index: RootIndex, *, line_offset: int = 0) -> None:
	text = _strip_css_comments(text)
	blocks = _parse_blocks(text)

	for block in blocks:
		if block.end == -1 or block.selector.startswith("@") or not block.selector:
			continue
		line = _line_at(text, block.start - 1) + line_offset
		for part in block.selector.split(","):
			for tok in _SELECTOR_TOKEN_RE.findall(part):
				root_index.add_selector_hit(SelectorHit(token=tok, kind="css", file=file_rel, line=line, detail="CSS rule"))

	for match in _VAR_DECL_RE.finditer(text):
		name, value = match.group(1), match.group(2).strip()
		context = _breadcrumb(_enclosing_block(blocks, match.start()))
		line = _line_at(text, match.start()) + line_offset
		root_index.add_declaration(VarDeclaration(name=name, value=value, context=context, file=file_rel, line=line))

	for match in _VAR_USE_RE.finditer(text):
		name = match.group(1)
		line = _line_at(text, match.start()) + line_offset
		root_index.add_usage(VarUsage(name=name, file=file_rel, line=line, has_fallback=bool(match.group(2))))


def _scan_html_text(text: str, file_rel: str, root_index: RootIndex) -> None:
	text = _strip_html_comments(text)

	for style_match in _STYLE_BLOCK_RE.finditer(text):
		inner = style_match.group(1)
		offset = _line_at(text, style_match.start(1)) - 1
		_scan_css_text(inner, file_rel, root_index, line_offset=offset)

	for attr_match in _STYLE_ATTR_RE.finditer(text):
		inner = attr_match.group(1)
		line = _line_at(text, attr_match.start(1))
		_scan_css_text(inner, file_rel, root_index, line_offset=line - 1)

	for match in _ID_ATTR_RE.finditer(text):
		line = _line_at(text, match.start())
		root_index.add_selector_hit(
			SelectorHit(token=f"#{match.group(1)}", kind="html", file=file_rel, line=line, detail="id attribute")
		)

	for match in _CLASS_ATTR_RE.finditer(text):
		line = _line_at(text, match.start())
		for token in match.group(1).split():
			root_index.add_selector_hit(
				SelectorHit(token=f".{token}", kind="html", file=file_rel, line=line, detail="class attribute")
			)


def _js_selector_tokens_from_string(value: str) -> list[str]:
	return _SELECTOR_TOKEN_RE.findall(value)


def _scan_js_text(text: str, file_rel: str, root_index: RootIndex) -> None:
	text = _strip_js_comments(text)

	for match in _JS_SETPROPERTY_RE.finditer(text):
		line = _line_at(text, match.start())
		root_index.add_usage(VarUsage(name=match.group(1), file=file_rel, line=line, has_fallback=True))

	for match in _JS_GETPROPERTYVALUE_RE.finditer(text):
		line = _line_at(text, match.start())
		root_index.add_usage(VarUsage(name=match.group(1), file=file_rel, line=line, has_fallback=True))

	for match in _JS_GET_ELEMENT_BY_ID_RE.finditer(text):
		literal, has_concat = match.group(1), bool(match.group(2))
		if not literal:
			continue
		line = _line_at(text, match.start())
		root_index.add_selector_hit(
			SelectorHit(
				token=f"#{literal}",
				kind="js",
				file=file_rel,
				line=line,
				detail="getElementById",
				dynamic=has_concat,
			)
		)

	for match in _JS_CLASSLIST_RE.finditer(text):
		method, args = match.group(1), match.group(2)
		line = _line_at(text, match.start())
		for literal in _STRING_LITERAL_RE.findall(args):
			root_index.add_selector_hit(
				SelectorHit(token=f".{literal}", kind="js", file=file_rel, line=line, detail=f"classList.{method}")
			)

	for match in _JS_QUERY_RE.finditer(text):
		line = _line_at(text, match.start())
		for token in _js_selector_tokens_from_string(match.group(1)):
			root_index.add_selector_hit(SelectorHit(token=token, kind="js", file=file_rel, line=line, detail="querySelector"))

	for match in _JS_CLASSNAME_ASSIGN_RE.finditer(text):
		line = _line_at(text, match.start())
		for token in match.group(1).split():
			root_index.add_selector_hit(SelectorHit(token=f".{token}", kind="js", file=file_rel, line=line, detail="className"))


def _relevant_files(root: Path) -> list[Path]:
	if not root.is_dir():
		return []
	files = [
		p
		for p in root.rglob("*")
		if p.is_file() and p.suffix.lower() in (".css", ".html", ".js") and "vendor" not in p.relative_to(root).parts
	]
	return sorted(files)


def build_root_index(root: Path, name: str) -> RootIndex:
	root_index = RootIndex(name=name, root=root)
	for path in _relevant_files(root):
		file_rel = str(path.relative_to(root)).replace("\\", "/")
		try:
			text = path.read_text(encoding="utf-8")
		except OSError:
			continue
		suffix = path.suffix.lower()
		if suffix == ".css":
			_scan_css_text(text, file_rel, root_index)
		elif suffix == ".html":
			_scan_html_text(text, file_rel, root_index)
		elif suffix == ".js":
			_scan_js_text(text, file_rel, root_index)
	return root_index


def build_workspace_index(workspace_root: Path) -> list[RootIndex]:
	return [
		build_root_index(workspace_root / STATIC_ROOT_REL, "static"),
		build_root_index(workspace_root / WIREFRAME_ROOT_REL, "wireframes"),
	]


def _normalize_var_name(name: str) -> str:
	name = name.strip()
	return name if name.startswith("--") else f"--{name}"


def token_kind(token: str) -> str | None:
	"""`'id'`/`'class'` for a `#foo`/`.foo` token, else `None`."""
	if token.startswith("#"):
		return "id"
	if token.startswith("."):
		return "class"
	return None


# -- formatting --------------------------------------------------------------


def _group_usages_by_file(usages: list[VarUsage]) -> list[tuple[str, list[int]]]:
	groups: dict[str, list[int]] = {}
	for u in usages:
		groups.setdefault(u.file, []).append(u.line)
	return sorted((f, sorted(set(lines))) for f, lines in groups.items())


def _group_hits_by_file(hits: list[SelectorHit]) -> list[tuple[str, list[SelectorHit]]]:
	groups: dict[str, list[SelectorHit]] = {}
	for h in hits:
		groups.setdefault(h.file, []).append(h)
	return sorted(groups.items())


def format_css_var(indexes: list[RootIndex], name: str) -> str:
	var_name = _normalize_var_name(name)
	sections: list[str] = []
	found = False
	for idx in indexes:
		decls = idx.var_declarations.get(var_name, [])
		uses = idx.var_usages.get(var_name, [])
		if not decls and not uses:
			continue
		found = True
		lines = [f"== {idx.name} =="]
		if decls:
			lines.append("Definitions:")
			lines += [f"  {d.file}:{d.line}  ({d.context or '(top level)'})  = {d.value}" for d in decls]
		else:
			lines.append("Definitions: (none)")
		if uses:
			by_file = _group_usages_by_file(uses)
			lines.append(f"Usages ({len(uses)} in {len(by_file)} file(s)):")
			lines += [f"  {f}: " + ", ".join(f"L{n}" for n in ns) for f, ns in by_file]
		else:
			lines.append("Usages: (none)")
		sections.append("\n".join(lines))
	if not found:
		return f"{var_name} is not defined or used anywhere under static/ or wireframes/."
	return f"{var_name}\n\n" + "\n\n".join(sections)


def format_selector(indexes: list[RootIndex], token: str) -> str:
	kind = token_kind(token)
	if kind is None:
		return f"{token!r} must start with '#' (id) or '.' (class)."
	sections: list[str] = []
	found = False
	for idx in indexes:
		hits = idx.selector_hits.get(token, [])
		if not hits:
			continue
		found = True
		lines = [f"== {idx.name} =="]
		for kind_label in ("html", "css", "js"):
			kind_hits = [h for h in hits if h.kind == kind_label]
			if not kind_hits:
				continue
			by_file = _group_hits_by_file(kind_hits)
			lines.append(f"{kind_label.upper()} ({len(kind_hits)}):")
			for f, file_hits in by_file:
				parts = []
				for h in sorted(file_hits, key=lambda h: h.line):
					tag = f"L{h.line}"
					if h.detail:
						tag += f" ({h.detail}{', dynamic partial match' if h.dynamic else ''})"
					parts.append(tag)
				lines.append(f"  {f}: " + ", ".join(parts))
		sections.append("\n".join(lines))
	if not found:
		return f"{token} was not found under static/ or wireframes/."
	return f"{token}\n\n" + "\n\n".join(sections)


# -- reference/definition/diagnostics enrichment ------------------------------

_CSS_TOKEN_UNDER_CURSOR_RE = re.compile(r"(--[a-zA-Z0-9_-]+|[.#][a-zA-Z_-][a-zA-Z0-9_-]*)")


def token_at_position(line_text: str, column: int) -> str | None:
	"""The `--var`, `#id` or `.class` token containing a 1-indexed `column`, if any."""
	idx = column - 1
	for match in _CSS_TOKEN_UNDER_CURSOR_RE.finditer(line_text):
		if match.start() <= idx < match.end():
			return match.group(1)
	return None


def root_index_for_file(indexes: list[RootIndex], file_path: Path) -> tuple[RootIndex, str] | None:
	for idx in indexes:
		try:
			rel = str(file_path.resolve().relative_to(idx.root.resolve())).replace("\\", "/")
		except ValueError:
			continue
		return idx, rel
	return None


def undefined_var_usages(idx: RootIndex) -> list[VarUsage]:
	return [
		usage
		for name, usages in idx.var_usages.items()
		for usage in usages
		if name not in idx.var_declarations and not usage.has_fallback
	]


def unreferenced_selectors(idx: RootIndex) -> list[str]:
	unreferenced = []
	for token, hits in idx.selector_hits.items():
		has_definition = any(h.kind == "css" for h in hits)
		has_reference = any(h.kind in ("html", "js") and not h.dynamic for h in hits)
		if has_definition and not has_reference:
			unreferenced.append(token)
	return sorted(unreferenced)


def diagnostics_for_file(idx: RootIndex, file_rel: str) -> list[str]:
	"""Index-derived warning lines for one file: undefined `var(--x)` usages
	(no fallback) and CSS selectors with no HTML/JS reference in this root.
	Dynamically-built JS selectors are skipped to avoid false positives."""
	warnings: list[str] = []
	for usage in undefined_var_usages(idx):
		if usage.file == file_rel:
			warnings.append(f"{usage.line}:1 [warning] var({usage.name}) is never defined in {idx.name}")
	unreferenced = set(unreferenced_selectors(idx))
	for token in unreferenced:
		for hit in idx.selector_hits.get(token, []):
			if hit.kind == "css" and hit.file == file_rel:
				warnings.append(f"{hit.line}:1 [warning] {token} is never referenced in {idx.name}'s HTML/JS")
	return sorted(warnings, key=lambda w: int(w.split(":", 1)[0]))
