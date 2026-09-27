# Decision log

One entry per decision. Newest at the bottom. Never delete an entry — mark it **Superseded by D-00X** instead.

## Template

```
## D-00X: <title>
- Date: YYYY-MM-DD
- Status: proposed | accepted | superseded
- Context: why a decision was needed
- Options: A / B / C (with trade-offs)
- Decision: what we chose
- Consequences: what this makes easier / harder
```

---

## D-001: Keep living docs in `docs/` alongside the code
- Date: 2026-09-27
- Status: accepted
- Context: The project will evolve as we learn how Inkscape behaves under automation.
- Decision: Markdown docs in-repo, updated in the same commit as related code.
- Consequences: Docs are versioned with code; history shows how thinking changed.

## D-002: Python + official MCP SDK (`mcp` 2.x `MCPServer`), managed with uv
- Date: 2026-09-27
- Status: accepted
- Options: Python (MCP SDK, lxml, same language as Inkscape extensions) vs TypeScript/Node.
- Decision: Python 3.12, `mcp>=2.2` (`from mcp.server.mcpserver import MCPServer` — FastMCP was renamed in 2.x), `lxml`, pytest. uv pins the interpreter.
- Consequences: In-process `mcp.Client(server)` makes end-to-end tests trivial.

## D-003: Experiment-driven development; tests are the real validation
- Date: 2026-09-27
- Status: accepted
- Context: Inkscape's automation behaviour is under-documented and surprising (exit codes, sticky state).
- Decision: Theory only at the level of principles. Every behaviour we rely on is first proven by a small script in `experiments/`, recorded as a finding in `05-inkscape-notes.md`, then guarded by a test against the real Inkscape.
- Consequences: Tests need Inkscape installed. Docs become an asset because each fact is backed by an experiment and a test.

## D-004: lxml document is the source of truth; Inkscape is a stateless worker behind a persistent shell
- Date: 2026-09-27
- Status: accepted
- Options: (A) spawn Inkscape per call — simple, ~1 s/call; (B) keep a document open inside the shell and mirror state — fast but two sources of truth; (C) lxml in Python owns the document, each Inkscape op writes a temp file, opens it in a persistent `--shell`, runs, exports back, closes.
- Decision: C.
- Consequences: Simple edits cost ~0 ms (pure lxml). Inkscape ops ~50–120 ms. No state drift. Must defend against sticky shell state (F5–F7). Possible later optimisation: keep the doc open while no lxml edits happen.

## D-005: No `inkex` dependency for now
- Date: 2026-09-27
- Status: accepted
- Context: inkex isn't on the bundled Python's path and pulls in extra deps.
- Decision: lxml for the DOM; Inkscape actions for geometry. Revisit if we need inkex's path/transform maths.

## D-006: Agent-facing output conventions
- Date: 2026-09-27
- Status: accepted
- Decision:
  - Tools return compact JSON text (no indentation, no duplicated structured content) to save agent tokens.
  - Expected failures raise `ToolError` so the agent sees the message. (MCP 2.x replaces other exception messages with a generic "Error executing tool X".)
  - All coordinates are in document user units; the server converts Inkscape's px.
  - `doc_id` is optional everywhere — tools act on the current document.
  - Editing tools accept `preview=true` and return the rendered PNG in the same call.
  - Batch tools (`add_elements`) are all-or-nothing and report the failing index.
