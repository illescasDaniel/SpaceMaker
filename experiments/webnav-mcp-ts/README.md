# webnav-mcp (TypeScript port, prototype)

A TypeScript port of the Python [`webnav-mcp`](https://github.com/illescasDaniel/webnav-mcp):
an MCP server that gives AI agents JS/TS/HTML/CSS navigation, plus a cross-file
index of CSS custom properties and `#id`/`.class` selectors that single-file
language servers can't provide.

The point of the port: a web project can add it with its own package manager,
and there is no Python or `uv` in the chain.

```bash
npm install --save-dev webnav-mcp
```

```json
{
	"mcpServers": {
		"webnav": { "command": "npx", "args": ["webnav-mcp"] }
	}
}
```

Tool names, parameter names (snake_case), environment variables
(`WEBNAV_MCP_WORKSPACE`, `WEBNAV_MCP_ROOTS`, `WEBNAV_MCP_EXCLUDE`) and output text
match the Python package, so existing prompts, hosts and `.mcp.json` files keep
working. See the [Python README](https://github.com/illescasDaniel/webnav-mcp#readme)
for the tool reference.

> **Status: prototype, in use by SpaceMaker.** Not published. SpaceMaker's `.mcp.json` /
> `.cursor/mcp.json` launch `bin/launch.mjs` from here, which installs and builds `dist/` on first start
> (`npm run setup:webnav` at the SpaceMaker root does it up front). Lives in `experiments/` of SpaceMaker
> (outside `src/spacemaker/`, so the SDD phase gates don't apply) to answer "is
> a port feasible?". The answer is in [Findings](#findings).

## Differences from the Python package

| | Python `webnav-mcp` | this port |
|---|---|---|
| Runtime | Python ≥ 3.11 **and** Node ≥ 18 | Node ≥ 20 only (tested on 22) |
| Language servers | found in the project's `node_modules`, then the package dir, then `PATH`, then `npx --yes` (downloads at first use) | ordinary npm dependencies: a TypeScript ≥ 7 in the *project* wins, else the copy installed with webnav. Nothing is downloaded at runtime |
| Launch | `.bin` shims (`.cmd` special case on Windows) | `node <server>.js`, no shims, no `PATH` dependence |
| JSON-RPC framing | hand-written | [`vscode-jsonrpc`](https://www.npmjs.com/package/vscode-jsonrpc) |
| UTF-16 columns | encode/decode helpers | JS strings already are UTF-16 |
| Cold start (init handshake) | ~1000 ms | ~280 ms |

## Layout

```
src/
  cli.ts          stdio entry point (exits when the host closes stdin)
  server.ts       registers the ten tools on the MCP SDK
  webnav.ts       the tools as plain async functions returning text; owns all state
  webIndex.ts     CSS var / selector index (port of web_index.py)
  langCommand.ts  how to launch tsc / html / css language servers
  glob.ts         just enough glob for jsconfig `include`
  shared/         port of mcp_nav_shared: lspClient, format, resolve, workspace,
                  notices, errors, params, exclude
tests/            vitest; fixtures/sample-app is the shared fixture
scripts/parity.mjs  drives Python and TS servers side by side and diffs the output
```

`shared/` is deliberately a directory, not a second package: see
[Shared library](#the-shared-library).

## Development

```bash
npm install
npm run check     # biome + tsc + vitest (pretest builds dist/)
npm run parity    # needs ../../../webnav-mcp checked out with `uv sync`; see the script header
```

## Findings

### Feasible: yes, and it is a mostly mechanical port

`webnav` is glue: it spawns three Node language servers and formats their answers,
plus a regex-grade index. Nothing in it depends on Python. The MCP SDK, the LSP
plumbing and the file scanning all have first-class Node equivalents.

**Behavioural parity**, measured by `scripts/parity.mjs` (real MCP over stdio,
identical calls, diffed text):

- SpaceMaker's own web assets (`.cursor/mcp.json` env, three roots): **37 / 37 identical**
- `tests/fixtures/sample-app`, including edits behind the servers' backs (fix a
  type error, create/delete a file, change a stylesheet, change `jsconfig.json`
  and get the restart notice): **71 / 71 identical** (counting the one intentional
  inherited-member difference below)

The one intentional difference is the reason string of "Cannot read file as
UTF-8 text: …", which is a Python codec detail; the parity script masks it.

**Tests:** 145 vitest tests (unit ports of the index/format tests, real
language servers against the fixture, MCP protocol over an in-memory transport
incl. worktree selection via client roots with a real `git worktree`, LSP
client failure modes, and the built executable). The Python side has ~260 tests
across the two packages; the port covers the behaviour that matters for the
tools, not every case one-to-one.

### Things the port surfaced

- **The MCP SDK's stdio server does not treat stdin EOF as a close.** With a
  language server child alive, the process kept running after the host went
  away (found by installing the tarball and launching via `npx`). `cli.ts` now
  handles `stdin` `end`/`close`; `tests/cli.test.ts` fails without it.
- **UTF-16 handling gets simpler:** JS strings are UTF-16, so the column
  conversion helpers in the Python `format.py`/`lsp_client.py` disappear.
- **One known regex divergence:** Python's `\w` is Unicode-aware, JS's is ASCII.
  The index regexes use `(?<![\w-])` to avoid matching `data-id=`; a non-ASCII
  letter directly before `id=`/`class=`/`style=` is treated differently (a
  match in JS, none in Python). Vanishingly rare in real markup, not covered by
  parity fixtures.
- **Inherited-member lookup needed a different approach.** The Python package
  finds `Class.member` for a member declared on a base class through the LSP's
  type hierarchy, but TypeScript 7's language server advertises no type
  hierarchy (checked against its `initialize` capabilities), so
  `symbol_info("Widget.greet")` used to say "not found" in both implementations.
  This port reads the `extends`/`implements` clauses from the source and resolves
  each base with `textDocument/definition`, breadth-first across files (generic
  bases, qualified names and mixin calls handled; `.d.ts`/`node_modules` bases
  aren't followed). It is the one intentional difference the parity script
  shows.
- **Two tools the Python webnav never had:** the same capability check showed the
  server offers `callHierarchyProvider` and `implementationProvider`, so this
  port adds `callers` and `implementations` (12 tools now; the Python one has 10).

### Costs

- **Install size:** a fresh app installing this next to its own TypeScript 5:
  177 MB `node_modules` (`vscode-langservers-extracted` 66 MB, TypeScript 7
  ~50 MB with its native binary). An app already on TypeScript ≥ 7 shares that
  copy. The Python package had the same npm payload, plus Python.
- **Code size:** ~4.2k lines of TypeScript (2.3k of it in `shared/`) vs ~3.7k
  lines of Python for webnav + the shared library (which also carries
  codenav-only code that wasn't ported).
- **Not ported** (codenav-only in the shared library): `typeDefinition`,
  scratch documents, source-root helpers. (Call hierarchy was ported after all,
  for `callers`.)
- **Not verified:** Windows, macOS, Node 20/24. Only Linux + Node 22.

### The shared library

The user-visible downside of the port is that `mcp-nav-shared` (LSP client,
formatting, symbol resolution, workspace selection) now exists twice. Options,
roughly in order of effort:

1. **Keep `src/shared/` internal to the TS package** (what this prototype does).
   Zero coordination cost; the two copies can drift. Mitigated by
   `scripts/parity.mjs`, which fails when their output diverges.
2. **Publish it as its own npm package** (`mcp-nav-shared`) only if a second TS
   server appears. `codenav` is tied to `ty` (Python) and has no reason to move.
3. **Retire the Python `webnav-mcp`** and keep only the TS one, leaving
   `mcp-nav-shared` for `codenav-mcp` alone. Removes the duplication, breaks
   `uvx webnav-mcp` users.

The Python shared library's webnav-relevant part is small (LSP client, format,
resolve, workspace, notices), which is why the duplication is tolerable.
