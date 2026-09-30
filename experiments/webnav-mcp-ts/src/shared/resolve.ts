/**
 * Name-based symbol resolution for the composite tools (`symbol_info`): a
 * `workspace/symbol` lookup with tiered ranking, dotted `Class.method`
 * resolution via `documentSymbol`, and disambiguation by `file_path`, so the
 * tools take a name instead of a hand-computed position.
 */

import { isToolError, ToolInputError } from "./errors.js";
import {
	filterWorkspaceSymbols,
	isHierarchicalDocumentSymbols,
	matchTier,
	pyRepr,
	rankWorkspaceSymbols,
	symbolKindLabel,
	toSymbolTree,
	uriToRelative,
	workspaceSymbolPosition,
} from "./format.js";
import type { LspClient } from "./lspClient.js";
import type { CallHierarchyItemLike, LspSymbol, SymbolNode } from "./lspTypes.js";

// SymbolKind values that are class members: a candidate with one of these gets
// qualified as `Class.member` in an ambiguity listing.
const MEMBER_KINDS = new Set([6, 7, 9]); // Method, Property, Constructor
const CLASS_KIND = 5;

/** No single confident match for a name-based symbol query: not found, or ambiguous. */
export class SymbolResolutionError extends ToolInputError {
	override name = "SymbolResolutionError";
}

export interface ResolvedSymbol {
	name: string;
	kind: number | undefined;
	uri: string;
	/** 0-based, aimed at the identifier. */
	line: number;
	column: number;
	/** The symbol's full span (for dotted member lookup). */
	rangeStartLine: number;
	rangeEndLine: number;
}

function resolvedFromSymbol(sym: LspSymbol): ResolvedSymbol {
	const [uri, line, column] = workspaceSymbolPosition(sym);
	const rng = sym.location?.range ?? {};
	const startLine = rng.start?.line ?? line;
	const endLine = rng.end?.line ?? startLine;
	return {
		name: sym.name || "?",
		kind: sym.kind,
		uri,
		line,
		column,
		rangeStartLine: startLine,
		rangeEndLine: endLine,
	};
}

function memberSpan(sym: LspSymbol): [number, number] {
	const rng = sym.location?.range ?? {};
	const start = rng.start?.line ?? 0;
	return [start, rng.end?.line ?? start];
}

/** Hierarchical `DocumentSymbol` named `name` (any depth), preferring the one whose identifier sits on `line`. */
function findNamedNode(symbols: LspSymbol[], name: string, line: number): LspSymbol | undefined {
	const found: LspSymbol[] = [];
	const walk = (nodes: LspSymbol[]): void => {
		for (const node of nodes) {
			if (String(node.name) === name) {
				found.push(node);
			}
			walk(node.children ?? []);
		}
	};
	walk(symbols);
	for (const node of found) {
		const sel = (node.selectionRange ?? node.range)?.start;
		if ((sel?.line ?? -1) === line) {
			return node;
		}
	}
	return found[0];
}

/** `memberName` directly under a node named `containerName` (nested classes too). */
function findMemberNode(symbols: LspSymbol[], containerName: string, memberName: string): LspSymbol | undefined {
	for (const node of symbols) {
		if (String(node.name) === containerName) {
			const child = (node.children ?? []).find((c) => String(c.name) === memberName);
			if (child) {
				return child;
			}
		}
		const found = findMemberNode(node.children ?? [], containerName, memberName);
		if (found) {
			return found;
		}
	}
	return undefined;
}

function resolvedFromHierarchicalNode(memberName: string, node: LspSymbol, uri: string): ResolvedSymbol {
	const selStart = node.selectionRange?.start ?? node.range?.start ?? {};
	const rng = node.range ?? {};
	const startLine = rng.start?.line ?? 0;
	const endLine = rng.end?.line ?? startLine;
	return {
		name: memberName,
		kind: node.kind,
		uri,
		line: selStart.line ?? startLine,
		column: selStart.character ?? 0,
		rangeStartLine: startLine,
		rangeEndLine: endLine,
	};
}

/** The Class node of a `toSymbolTree` hierarchy whose range contains `targetLine`, innermost first. */
function enclosingClassName(nodes: SymbolNode[], targetLine: number): string | undefined {
	for (const node of nodes) {
		if (!(node.startLine <= targetLine && targetLine <= node.endLine)) {
			continue;
		}
		const inner = enclosingClassName(node.children, targetLine);
		if (inner !== undefined) {
			return inner;
		}
		return node.kind === CLASS_KIND ? node.name : undefined;
	}
	return undefined;
}

/** For Method/Property/Constructor candidates, resolve their enclosing class so an ambiguity listing can show `Class.member`. */
async function qualifyCandidates(
	client: LspClient,
	workspaceRoot: string,
	candidates: LspSymbol[],
): Promise<Map<number, string>> {
	const qualified = new Map<number, string>();
	const trees = new Map<string, SymbolNode[]>();
	for (const [i, sym] of candidates.entries()) {
		if (sym.kind === undefined || !MEMBER_KINDS.has(sym.kind)) {
			continue;
		}
		const rel = uriToRelative(sym.location?.uri ?? "", workspaceRoot);
		let tree = trees.get(rel);
		if (tree === undefined) {
			try {
				tree = toSymbolTree(await client.documentSymbol(rel));
			} catch (error) {
				if (!isToolError(error)) {
					throw error;
				}
				tree = [];
			}
			trees.set(rel, tree);
		}
		const className = enclosingClassName(tree, memberSpan(sym)[0]);
		if (className) {
			qualified.set(i, className);
		}
	}
	return qualified;
}

async function formatCandidates(client: LspClient, candidates: LspSymbol[], workspaceRoot: string): Promise<string> {
	const shown = candidates.slice(0, 10);
	const qualified = await qualifyCandidates(client, workspaceRoot, shown);
	return shown
		.map((sym, i) => {
			const name = sym.name || "?";
			const qualifier = qualified.get(i);
			const display = qualifier ? `${qualifier}.${name}` : name;
			const [uri, line, col] = workspaceSymbolPosition(sym);
			const rel = uri ? uriToRelative(uri, workspaceRoot) : "?";
			return `${display}  [${symbolKindLabel(sym.kind)}]  (${rel}:${line + 1}:${col + 1})`;
		})
		.join("\n");
}

const notFound = (query: string): SymbolResolutionError =>
	new SymbolResolutionError(`No symbol found matching ${pyRepr(query)}.`);

async function ambiguous(
	client: LspClient,
	query: string,
	candidates: LspSymbol[],
	workspaceRoot: string,
): Promise<SymbolResolutionError> {
	const sameFile = new Set(candidates.map((c) => c.location?.uri ?? "")).size === 1;
	// Narrowing by file_path still leaves several same-named symbols in one file
	// (a module-level function and a same-named class method), so point at the
	// position-based escape hatch instead of advice that won't help.
	const hint = sameFile
		? "these all live in the same file; use search_symbol to get exact line/column, then hover/definition/references with that position"
		: "pass file_path to disambiguate";
	return new SymbolResolutionError(
		`${candidates.length} symbols match ${pyRepr(query)}; ${hint}:\n${await formatCandidates(client, candidates, workspaceRoot)}`,
	);
}

function matchesFile(sym: LspSymbol, workspaceRoot: string, filePath: string): boolean {
	const rel = uriToRelative(sym.location?.uri ?? "", workspaceRoot);
	const target = filePath.replaceAll("\\", "/");
	return rel === target || rel.endsWith(`/${target}`) || target.endsWith(`/${rel}`);
}

async function exactCandidates(
	client: LspClient,
	workspaceRoot: string,
	name: string,
	filePath: string | undefined,
): Promise<LspSymbol[]> {
	const symbols = await client.workspaceSymbol(name);
	// Same filter as search_symbol: drop export-list Variable twins and identical
	// (name, kind, file) dupes so `symbol_info("foo")` isn't ambiguous between
	// `function foo` and `export { foo }`.
	const ranked = filterWorkspaceSymbols(rankWorkspaceSymbols(symbols, name));
	let exact = ranked.filter((s) => matchTier(s.name ?? "", name) <= 1);
	// Prefer a case-exact match over a merely case-insensitive one when both exist.
	const caseExact = exact.filter((s) => matchTier(s.name ?? "", name) === 0);
	if (caseExact.length > 0) {
		exact = caseExact;
	}
	if (filePath !== undefined) {
		const narrowed = exact.filter((s) => matchesFile(s, workspaceRoot, filePath));
		if (exact.length > 0 && narrowed.length === 0) {
			// Silently answering with a symbol from a different file than the one the
			// caller named would be a confidently wrong result.
			throw new SymbolResolutionError(
				`No symbol ${pyRepr(name)} in ${pyRepr(filePath)}; ${exact.length} match(es) elsewhere:\n` +
					(await formatCandidates(client, exact, workspaceRoot)),
			);
		}
		exact = narrowed;
	}
	return exact;
}

async function resolveSimple(
	client: LspClient,
	workspaceRoot: string,
	query: string,
	filePath: string | undefined,
): Promise<ResolvedSymbol> {
	const exact = await exactCandidates(client, workspaceRoot, query, filePath);
	const [only, ...rest] = exact;
	if (only === undefined) {
		throw notFound(query);
	}
	if (rest.length > 0) {
		throw await ambiguous(client, query, exact, workspaceRoot);
	}
	return resolvedFromSymbol(only);
}

async function resolveDotted(
	client: LspClient,
	workspaceRoot: string,
	query: string,
	filePath: string | undefined,
): Promise<ResolvedSymbol> {
	// `Outer.Inner.method`: the first segment is looked up workspace-wide, the
	// rest are walked down through that symbol's document-symbol tree.
	const [first = "", ...parts] = query.split(".");
	const memberName = parts[parts.length - 1] ?? "";
	const container = await resolveSimple(client, workspaceRoot, first, filePath);
	const relPath = uriToRelative(container.uri, workspaceRoot);
	const members = await client.documentSymbol(relPath);
	if (isHierarchicalDocumentSymbols(members)) {
		let found = findNamedNode(members, container.name, container.line);
		for (const part of parts) {
			found = (found?.children ?? []).find((c) => String(c.name) === part);
		}
		if (found) {
			return resolvedFromHierarchicalNode(memberName, found, container.uri);
		}
	} else {
		// Flat `SymbolInformation`: narrow by range containment one segment at a time.
		let span: [number, number] = [container.rangeStartLine, container.rangeEndLine];
		let match: LspSymbol | undefined;
		for (const part of parts) {
			const candidates = members.filter((m) => {
				const [start, end] = memberSpan(m);
				return (
					String(m.name ?? "") === part &&
					span[0] <= start &&
					start <= span[1] &&
					!(start === span[0] && end === span[1])
				);
			});
			if (candidates.length > 1) {
				throw await ambiguous(client, query, candidates, workspaceRoot);
			}
			const [only] = candidates;
			if (only === undefined) {
				match = undefined;
				break;
			}
			match = only;
			span = memberSpan(only);
		}
		if (match) {
			return resolvedFromSymbol(match);
		}
	}
	// Inherited members only make sense for a plain `Class.member` query.
	const inherited =
		parts.length === 1 ? await resolveInherited(client, workspaceRoot, container, memberName) : undefined;
	if (inherited === undefined) {
		throw notFound(query);
	}
	return inherited;
}

// Guards against pathological (or cyclic) hierarchies; real class graphs are far smaller.
const MAX_SUPERTYPES_VISITED = 64;

/**
 * `Class.member` where `member` is inherited. Walks `typeHierarchy/supertypes`
 * breadth-first and returns the first supertype that declares `member`
 * directly; `undefined` when the server doesn't support type hierarchy.
 */
async function resolveInherited(
	client: LspClient,
	workspaceRoot: string,
	container: ResolvedSymbol,
	memberName: string,
): Promise<ResolvedSymbol | undefined> {
	const relPath = uriToRelative(container.uri, workspaceRoot);
	let queue: CallHierarchyItemLike[];
	try {
		queue = [...(await client.prepareTypeHierarchy(relPath, container.line + 1, container.column + 1))];
	} catch (error) {
		if (!isToolError(error)) {
			throw error;
		}
		return undefined;
	}
	const seen = new Set<string>();
	while (queue.length > 0 && seen.size < MAX_SUPERTYPES_VISITED) {
		const item = queue.shift() as CallHierarchyItemLike;
		let supers: CallHierarchyItemLike[];
		try {
			supers = await client.supertypes(item);
		} catch (error) {
			if (!isToolError(error)) {
				throw error;
			}
			continue;
		}
		for (const sup of supers) {
			const uri = String(sup.uri ?? "");
			const name = String(sup.name ?? "");
			const key = `${uri}\0${name}`;
			if (seen.has(key)) {
				continue;
			}
			seen.add(key);
			queue.push(sup);
			let members: LspSymbol[];
			try {
				members = await client.documentSymbol(uriToRelative(uri, workspaceRoot));
			} catch (error) {
				if (!isToolError(error)) {
					throw error;
				}
				continue; // e.g. a stdlib/vendored base the server reports by a non-file URI
			}
			if (!isHierarchicalDocumentSymbols(members)) {
				continue;
			}
			const node = findMemberNode(members, name, memberName);
			if (node) {
				return resolvedFromHierarchicalNode(memberName, node, uri);
			}
		}
	}
	return undefined;
}

/**
 * Resolve a name (or dotted `Class.method`) to a single symbol position.
 *
 * Throws `SymbolResolutionError` (a `ToolInputError`) when nothing matches or
 * several symbols tie on an exact name: callers should pass `file_path` to
 * disambiguate rather than guess.
 */
export function resolveSymbol(
	client: LspClient,
	workspaceRoot: string,
	query: string,
	filePath?: string,
): Promise<ResolvedSymbol> {
	return query.includes(".")
		? resolveDotted(client, workspaceRoot, query, filePath)
		: resolveSimple(client, workspaceRoot, query, filePath);
}
