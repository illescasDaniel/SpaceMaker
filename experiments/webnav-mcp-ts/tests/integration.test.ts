/** Real language servers (TypeScript 7 `tsc --lsp`, vscode HTML/CSS) against a copy of the sample app. */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { Webnav } from "../src/webnav.js";
import { makeTree } from "./helpers.js";

const fixture = path.join(path.dirname(fileURLToPath(import.meta.url)), "fixtures/sample-app");
const sleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));

let ws: string;
let webnav: Webnav;
const savedEnv = { ...process.env };

function start(env: Record<string, string> = {}): Webnav {
	ws = makeTree();
	fs.cpSync(fixture, ws, { recursive: true });
	Object.assign(process.env, { WEBNAV_MCP_WORKSPACE: ws, ...env });
	webnav = new Webnav();
	return webnav;
}

beforeEach(() => {
	delete process.env.WEBNAV_MCP_ROOTS;
	delete process.env.WEBNAV_MCP_EXCLUDE;
});

afterEach(async () => {
	await webnav?.dispose();
	for (const key of Object.keys(process.env)) {
		if (!(key in savedEnv)) delete process.env[key];
	}
	Object.assign(process.env, savedEnv);
});

const T = 30_000;

describe("typescript navigation", () => {
	it(
		"given a class file, when outlined, then members appear in source order with spans",
		async () => {
			const text = await start().outline("src/app.ts");
			expect(text.split("\n").slice(0, 4)).toEqual([
				"Options  [Interface]  :1-3",
				"  title  [Property]  :2",
				"Base  [Class]  :5-9",
				"  greet  [Method]  :6-8",
			]);
		},
		T,
	);

	it(
		"given a name, when asking symbol_info, then header, hover, definition and grouped references come back",
		async () => {
			const text = await start().symbolInfo({ name: "makeWidget" });
			expect(text).toContain("makeWidget  [Function]  (src/app.ts:25:17)");
			expect(text).toContain("function makeWidget(title: string): Widget");
			expect(text).toMatch(
				/References:\n\d+ reference\(s\) in \d+ file\(s\):\nsrc\/app\.ts: L25\nsrc\/broken\.ts: L1, L4/,
			);
		},
		T,
	);

	it(
		"given a dotted name, when resolved, then the member is found; a missing member is reported",
		async () => {
			const w = start();
			expect(await w.symbolInfo({ name: "Widget.render" })).toContain("render  [Method]  (src/app.ts:17:2)");
			expect(await w.symbolInfo({ name: "Widget.nope" })).toBe("No symbol found matching 'Widget.nope'.");
		},
		T,
	);

	it(
		"given the same name in two files, when file_path is omitted, then the ambiguity is listed; file_path disambiguates",
		async () => {
			const w = start();
			fs.writeFileSync(path.join(ws, "src/dup.ts"), "export function makeWidget(): void {}\n");
			const ambiguous = await w.symbolInfo({ name: "makeWidget" });
			expect(ambiguous).toContain("2 symbols match 'makeWidget'; pass file_path to disambiguate:");
			expect(await w.symbolInfo({ name: "makeWidget", filePath: "src/dup.ts" })).toContain("(src/dup.ts:1:17)");
			expect(await w.symbolInfo({ name: "makeWidget", filePath: "src/util.js" })).toMatch(
				/^No symbol 'makeWidget' in 'src\/util\.js'; 2 match\(es\) elsewhere:/,
			);
		},
		T,
	);

	it(
		"given columns after an astral character, when hovering, then UTF-16 offsets address the right token",
		async () => {
			const w = start();
			const line = fs
				.readFileSync(path.join(ws, "src/app.ts"), "utf8")
				.split("\n")
				.findIndex((l) => l.includes("afterEmoji"));
			const column =
				(fs.readFileSync(path.join(ws, "src/app.ts"), "utf8").split("\n")[line] as string).indexOf("afterEmoji") + 1;
			expect(await w.hover("src/app.ts", line + 1, column)).toBe("const afterEmoji: 1");
		},
		T,
	);

	it(
		"given a position past the end, when hovering, then a clear range error is returned",
		async () => {
			const w = start();
			expect(await w.hover("src/app.ts", 9999, 1)).toMatch(
				/^line 9999 is out of range: src\/app\.ts has \d+ line\(s\)/,
			);
			expect(await w.hover("src/app.ts", 1, 9999)).toMatch(
				/^column 9999 is out of range: line 1 of src\/app\.ts is \d+ character\(s\) long/,
			);
		},
		T,
	);

	it(
		"given type errors, when diagnosing, then the compiler's diagnostics are listed; a fix behind its back clears them",
		async () => {
			const w = start();
			const before = await w.diagnostics("src/broken.ts");
			expect(before).toContain("[error 2322] Type 'string' is not assignable to type 'number'.");
			fs.writeFileSync(path.join(ws, "src/broken.ts"), "export const fine = 1;\n");
			await sleep(1100);
			expect(await w.diagnostics("src/broken.ts")).toBe("No diagnostics.");
		},
		T,
	);

	it(
		"given a file created after startup, when searching, then it is found without a restart",
		async () => {
			const w = start();
			await w.outline("src/app.ts");
			fs.writeFileSync(path.join(ws, "src/late.ts"), "export function arrivedLate(): void {}\n");
			expect(await w.searchSymbol({ query: "arrivedLate" })).toBe("arrivedLate  [Function]  (src/late.ts:1:17)");
			fs.rmSync(path.join(ws, "src/late.ts"));
			expect(await w.searchSymbol({ query: "arrivedLate" })).toBe("No symbols matching 'arrivedLate'.");
		},
		T,
	);

	it(
		"given a config file change, when the next tool runs, then the server restarts and says so once",
		async () => {
			const w = start();
			await w.outline("src/app.ts");
			fs.writeFileSync(
				path.join(ws, "jsconfig.json"),
				JSON.stringify({ compilerOptions: { allowJs: true }, include: ["src/**/*"] }),
			);
			const first = await w.outline("src/app.ts");
			expect(first).toContain("[webnav] restarted the language server because jsconfig.json changed");
			expect(await w.outline("src/app.ts")).not.toContain("restarted");
		},
		T,
	);

	it(
		"given a touched-but-identical config, when the next tool runs, then no restart happens",
		async () => {
			const w = start();
			await w.outline("src/app.ts");
			const file = path.join(ws, "jsconfig.json");
			fs.writeFileSync(file, fs.readFileSync(file));
			expect(await w.outline("src/app.ts")).not.toContain("restarted");
		},
		T,
	);

	it(
		"given generated output configured, when navigating it, then position tools refuse and search hides it",
		async () => {
			const w = start({ WEBNAV_MCP_EXCLUDE: "src/util.js" });
			expect(await w.outline("src/util.js")).toBe(
				"'src/util.js' is generated output (WEBNAV_MCP_EXCLUDE); navigate the source it was built from instead",
			);
			expect(await w.searchSymbol({ query: "debounce" })).toBe("No symbols matching 'debounce'.");
			expect(await w.selectorLookup({ name: "#btn-save" })).toContain("src/util.js [generated]");
		},
		T,
	);

	it(
		"given a non-script file, when outlined, then the error points at css_var/selector",
		async () => {
			expect(await start().outline("styles.css")).toContain("use css_var/selector for CSS/HTML");
		},
		T,
	);

	it(
		"given an invalid kind filter, when searching, then the valid kinds are listed",
		async () => {
			expect(await start().searchSymbol({ query: "x", kind: "nonsense" })).toMatch(
				/^unknown symbol kind 'nonsense'; use one or more of:/,
			);
		},
		T,
	);

	it(
		"given no name, when searching, then a hint mentions the alias",
		async () => {
			expect(await start().searchSymbol({})).toBe(
				"Pass `query` (e.g. query='renderSidebar'); `name` is accepted as an alias.",
			);
		},
		T,
	);
});

describe("html and css", () => {
	it(
		"given a css file, when diagnosing, then index warnings for undefined vars and unreferenced rules appear",
		async () => {
			const text = await start().diagnostics("styles.css");
			expect(text).toContain("[warning] var(--missing) is never defined in web");
			expect(text).toContain("[warning] .unused-class is never referenced in web's HTML/JS");
		},
		T,
	);

	it(
		"given a token in css, when asking references/definition, then the cross-file index answers",
		async () => {
			const w = start();
			const references = await w.references("styles.css", 20, 1); // `.widget`
			expect(references).toContain(".widget\n\n== web ==");
			expect(references).toContain("src/app.ts: L19 (classList.add), L20 (querySelector)");
			const definition = await w.definition("styles.css", 20, 1);
			expect(definition).toContain("CSS (2)"); // `.widget {` and `.widget .title {`
			expect(definition).not.toContain("JS (");
		},
		T,
	);

	it(
		"given a colour that looks like a selector, when asking references, then the language server answers instead of the index",
		async () => {
			const w = start();
			const text = await w.references("styles.css", 2, 15); // `#06c` in `--accent: #06c;`
			expect(text).not.toContain("== web ==");
		},
		T,
	);

	it(
		"given named roots, when a position is queried, then only that file's root answers unless it has nothing",
		async () => {
			const w = start({ WEBNAV_MCP_ROOTS: "design=design,app=src" });
			fs.mkdirSync(path.join(ws, "design"));
			fs.writeFileSync(path.join(ws, "design/d.css"), ":root { --accent: #f00; }\n.tile { color: var(--accent); }\n");
			const text = await w.cssVar({ name: "--accent" });
			expect(text).toContain("== design ==\nDefinitions:\n  design/d.css:1  (:root)  = #f00");
			expect(text).toContain("== app ==\nDefinitions: (none)");
			const scoped = await w.references("design/d.css", 2, 20); // `--accent` inside var(...)
			expect(scoped).toContain("== design ==");
			expect(scoped).not.toContain("== app ==");
		},
		T,
	);

	it(
		"given a malformed roots env, when using an index tool, then the misconfiguration is reported as text",
		async () => {
			expect(await start({ WEBNAV_MCP_ROOTS: "oops" }).cssVar({ name: "--a" })).toBe(
				"WEBNAV_MCP_ROOTS is misconfigured: invalid WEBNAV_MCP_ROOTS entry 'oops'; expected label=relative/path",
			);
		},
		T,
	);

	it(
		"given the workspace tool, then it names the root and why",
		async () => {
			expect(await start().workspace()).toBe(
				`${ws}\nchosen because: pinned by $WEBNAV_MCP_WORKSPACE; client roots are ignored`,
			);
		},
		T,
	);
});
