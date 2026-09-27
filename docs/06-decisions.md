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

## D-007: `align` computes moves in Python from measured boxes; Inkscape only measures and translates
- Date: 2026-09-27
- Status: accepted
- Context: Agents had to guess text baselines and compute positions (E06). Inkscape's `object-align` works headless (F12) but only knows visual bboxes and one reference per call.
- Options: (A) wrap `object-align`; (B) own maths in `layout.py` + Inkscape `transform-translate` to apply moves.
- Decision: B. One measurement pass (`query-all`, including "cap box" probes for text), all operations computed in order with a moving cache, one translate pass.
- Consequences:
  - Text is centred by **cap box** (cap height of line 1 → baseline of last line), measured per font by rendering an "H"-ified clone (S4). Labels in a row get identical baselines.
  - Any number of operations cost the same two Inkscape round-trips.
  - Inkscape handles transforms, groups and text when moving; we just convert user units → px (F13).
  - Ancestor bboxes are not refreshed in the cache after a child moves (edge case, not needed yet).

## D-008: `connect` uses native Inkscape connectors + one arrow marker per colour
- Date: 2026-09-27
- Status: accepted
- Options: (A) compute our own static routes and re-route after our moves; (B) native connectors (F15–F16).
- Decision: B. Inkscape routes, clips to real shapes and keeps connectors attached — also for a human editing later in the Inkscape GUI. Every Inkscape round-trip refreshes routes; tools that edit geometry via lxml only (`update_elements`) call `Engine.sync` when connectors exist. Arrowheads: per-colour markers (`inksmcp-arrow-<colour>`, tip at refX) rather than `context-stroke`, for portability to browsers.
- Consequences: Routes in lxml are stale between an lxml-only edit and the next sync (export/preview are unaffected, since Inkscape re-routes on load). Connector labels are our own text elements linked by `inksmcp:label-for` and re-centred on the route midpoint after each round-trip, using the approximate cap height (S4) — no extra measurement. Text endpoints are allowed but warned about (F17).

## D-009: `layout` arranges *items*, and tools report off-page results
- Date: 2026-09-27
- Status: accepted
- Decision: An item is an id or a list of ids moved as a unit (box + its label) — no grouping needed. Pure `layout.arrange` computes offsets; the block keeps the first item's position, or goes to `at`, or is aligned to `to`. `align` and `layout` return `warnings` when moved elements extend beyond the page (E10: the agent did not notice a clipped box in the preview).

## D-010: `page_fit` / `page_resize` in Python; the page origin always stays 0,0
- Date: 2026-09-27
- Status: accepted
- Options: (A) Inkscape `page-fit-to-selection` (F18: no margin, leaves backgrounds behind, needs a selection that excludes backgrounds); (B) set a non-zero viewBox origin (no content moves, but "top-left is 0,0" breaks for the agent); (C) measure, move all top-level content by (margin − origin) via `Engine.translate`, set size/viewBox, resize backgrounds.
- Decision: C. Backgrounds = top-level untransformed rects exactly covering the page (`Document.page_backgrounds`). `page_resize` sets an exact size (e.g. A4) with anchor top-left or center.
- Consequences:
  - The agent's coordinate model never changes.
  - Layers carry the move as `translate()` (same as Inkscape's own behaviour).
  - Connectors are never translated directly (F20).
  - Every move is snapped to 0.001 units and the moved elements' numbers tidied to 4 decimals (F14, F19).

## D-011: Z-order — exact ops in lxml, visual ops via Inkscape, reparenting keeps position
- Date: 2026-09-27
- Status: accepted
- Decision:
  - `front`/`back`/`above`/`below` are plain lxml reorders: instant, deterministic, several ids keep their order.
  - `forward`/`backward` wrap Inkscape's overlap-based raise/lower, one id at a time (F22). The result says when nothing changed and why.
  - `above`/`below` a target in another layer/group, and `move_to_layer`, reparent with transform compensation: new transform = inv(CTM(new parent)) · CTM(old parent) · own transform (`layout.py` affine helpers). Connectors are moved without compensation and re-synced (F20).
- Consequences: The agent can say "put the highlight above the photo" without caring which layer either lives in.
