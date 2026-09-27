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

## D-012: Preview zooms, export isolates
- Date: 2026-09-27
- Status: accepted
- Context: Field report 2026-09-27: `render_preview(ids)` drew only those ids (the agent expected a zoom) and failed for several ids (F23).
- Decision: `render_preview` with `ids` or `region` = that area with everything visible; `only_ids=true` isolates. `export` keeps "only these objects" as default for `ids` (exporting an icon), with `only_ids=false` and `region` available. Several isolated ids: hide everything else in a scratch copy and export the union area (export-id takes one id).

## D-013: `grid` — graph paper as one path per weight class, labels measured
- Date: 2026-09-27
- Status: accepted
- Context: The field test's biggest cost was computing ~335 log-scale positions outside the tools and guessing label offsets.
- Decision: Pure tick maths in `grids.py` (linear: major/medium/minor spacing; log: cycles with stationery subdivisions 0.1/0.2/0.5). One path per class in its own layer (finest at the bottom), border replaces edge lines, labels placed with the new text `vertical_anchor` (cap-box measured, E07). Default weights 0.45/0.22/0.08 mm, border 0.6 mm (taken from the field test's good result).
- Consequences: Log/linear paper, chart axes and diagram background grids in one call. Text `vertical_anchor` (top/middle/bottom) is available to every `add_elements` text as a by-product.

## D-014: Batch shell work — group moves by delta, join actions into long lines
- Date: 2026-09-27
- Status: accepted
- Decision: `translate` puts all elements with the same (dx, dy) into one selection; `run_actions` joins actions with `;` into lines ≤ 15,000 chars (F25).
- Consequences: Per-action error attribution in stderr is lost within a line (messages are still collected and still raise); acceptable given 9–150× speed-ups.

## D-015: Text layout — explicit line positions, measured wrapping
- Date: 2026-09-27
- Status: accepted
- Decision: Multi-line text = role=line tspans + `line-height` + explicit `y` per line (F26); x/y/size/line-height updates re-lay out the lines. `width` wraps greedily using word widths measured by Inkscape probes (one pass); the unwrapped source is kept in `inksmcp:paragraphs` so re-wrapping never loses paragraph breaks. Not SVG2 `inline-size` (F28).

## D-016: Connectors with sides/waypoints are routed by inksmcp
- Date: 2026-09-27
- Status: accepted
- Context: Field report 2 needed invisible helper objects and split connectors for a loop; Inkscape ignores connection points (F27).
- Decision: `from_side`/`to_side`/`via` switch a connector to our router (`layout.route`): endpoints at bbox side midpoints; elbow = best of four ≤2-corner candidates that neither double back nor cross either box. The spec lives in `inksmcp:route`; routes are recomputed after every translate and in `sync`, in the connector's parent coordinates. Plain connectors stay native (live in the Inkscape GUI).
- Label placement for both kinds: `label_position` or the middle of the longest segment (never a corner), `label_side` in screen terms (above/below/left/right/auto), halo only when on the line. A first version used "left of travel direction" — even its author got the sign wrong, so it was replaced.

## D-017: `plot` maps data through the grid's own axes
- Date: 2026-09-27
- Status: accepted
- Decision: `grid` stores its rect and axis specs (`inksmcp:grid`); `plot` maps data values with `grids.axis_mapper` (linear: label_start/label_step; log: `start`, one decade per cycle), draws line + markers + haloed point labels (placed on the side the line is not heading to), warns about out-of-range points. `grid` labels gained `x_title`/`y_title`, positioned from the measured tick labels.

## D-018: `plot` outputs are named after the series; label styling is explicit
- Date: 2026-09-27
- Status: accepted
- Context: Field report 3: the agent had to copy generic ids (`polyline82`) back from responses, guessed the label anchor 1 mm wrong, and turned haloed labels into white blobs by recolouring them.
- Decision: Children of a series group get `<id>-line`, `<id>-marker-k`, `<id>-label-k` (k = 1-based point index, `free_id` on clashes). `label_halo` (default white, `"none"`) and `label_anchor` (start/middle/end) are options; the tool description states the vertical centring on point + dy and the halo side effect. Grid axes take `"lines": false` instead of a separate gridline option, so the axis still maps data and carries labels.
- Consequences: Bar-style charts (thick `marker: none` series) need no follow-up fixes (E19). Real bar series / category axes stay on the backlog.

## D-019: `repeat` stamps rows as translated groups; mirroring keeps text readable
- Date: 2026-09-27
- Status: accepted
- Context: Field report 3's biggest cost: a timeline of 8 alternating cards (~60 elements) with every position computed by hand. The agent asked for a template stamped per data row, with alternate mirroring.
- Decision: The template is drawn for the first row. Each row becomes a group `<id_prefix>-<n>` with `translate(offset)`, so any element type (paths, arrows, existing transforms) works without rewriting geometry. Placeholders are `{key}`, and a value that is exactly one placeholder keeps its type. Template ids are local names suffixed `-<n>`, and `parent` can point to another template element. Mirroring works in document coordinates, T' = P⁻¹·M·P·T (F29): shapes are reflected, while texts and groups move so that their measured bbox is reflected (after wrapping), so glyphs never flip. A per-element `mirror` overrides this. Template elements can't carry `layer`; `layer` goes on the call.
- Rejected: reflecting everything (text would read backwards) and moving everything as blocks (pointers would not flip). Also rejected: moving texts individually as blocks. That breaks the layout inside a card (the year would jump to the card's right edge), so the tool description says to group a card with its texts.
- Consequences: The E20 timeline sends 37 % less request text at 4 rows. The template cost is fixed, so the saving grows with the number of rows. Rows with different heights still need a follow-up `update_elements` (future: rect `fit_to`).

## D-020: `fit_to` is a stored rect option, refitted on edits (not on moves)
- Date: 2026-09-27
- Status: accepted
- Context: Field report 3 estimated card heights from font metrics and needed a second `update_elements`. With `repeat`, rows have different amounts of text.
- Decision: `fit_to`/`fit_padding`/`fit` are rect keys, stored as `inksmcp:fit` JSON. After every add/update/repeat (after wrapping and anchoring, before `repeat` mirroring), rects that were touched or whose targets were touched are refitted with one measurement, in dependency order, so a panel fitted around cards follows the cards. The box is the union of the targets' *visual* bboxes (ink, including descenders), mapped into the rect's own coordinates. `fit: height` keeps a card's designed width.
- Rejected: refitting after every translate (an extra measurement for every align/layout, usually a no-op because cards move together with their texts); a separate `card` element type (fit_to also covers panels, highlights, legends).
- Consequences: The E20 timeline is back to 4 calls with no hand-computed heights. After moving targets on their own, `update_elements {"id": rect}` refits.
