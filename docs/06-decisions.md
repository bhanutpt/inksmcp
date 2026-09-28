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

## D-021: Field-test round 2 collects before it builds
- Date: 2026-09-28
- Status: accepted
- Context: Round 1 fixed each report's follow-ups right away (D-012–D-020). That worked, but each fix was shaped by one task. Several open needs (stacking by measured bbox, text runs, bulk edits, overflow warnings) keep recurring in different forms.
- Decision: For the next field tests, run several varied tasks first and record each report with a "Common or task-specific?" table. Only fix bugs straight away. Build features after a synthesis step that merges the tables and ranks needs by how often they occur and how much rework they cause. Then follow the usual experiment → test → code.
- Rejected: fixing each report immediately (it risks narrow options on top of options); a big design up front without usage data.
- Consequences: Field-report follow-ups are marked "Deferred to the round-2 synthesis" until then. The Tamil alphabet poster (2026-09-28) is the first report in this round.

## D-022: Every tool is all-or-nothing; one shell pass is retried once
- Date: 2026-09-28
- Status: accepted
- Context: Field report 5: the shell died in the middle of `add_elements`. The 37 elements were already in the document, but wrapping, `vertical_anchor` and `fit_to` never ran, and the error didn't say so. E23 could not reproduce the crash in 200 busy iterations; the transcript shows it was the first command after ~28 idle minutes. E23b reproduced it once in 5 idle runs (not deterministic in idle time); E23c ruled out other Inkscape instances.
- Decision: Two layers. (1) `Engine._pass` runs open → commands → close; if the process dies (`ShellDied`), the pass is repeated once on a fresh shell. That is safe because a pass only reads a temp copy of the document. (2) The MCP `tool` wrapper snapshots the target document (a deep copy of the tree, cheap even at 600 elements) and restores it on **any** exception; errors then end with "(Nothing was changed.)". `ShellDied` reports the exit code and the command it was running, for next time.
- Rejected: per-tool cleanup (add/repeat had it, update/grid/plot didn't, and it missed post-processing failures); reporting "written but not fitted" (the agent would have to repair it); restarting the shell after idle periods (idle shells survived 4–15 min in 4 of 5 runs, so idleness alone isn't the cause; the retry costs the same ~1 s startup anyway).
- Consequences: A one-off crash is invisible to the agent; a persistent one leaves the document as it was. The snapshot also makes validation failures in `update_elements` atomic, which they weren't.

## D-023: Grid spacings must nest; log labels follow `start`
- Date: 2026-09-28
- Status: accepted
- Context: Field report 10: `major: 11.6667, minor: 2.3333` silently dropped the x majors and their labels (lines were classed by a float-multiple test), and log labels read 1..9 per cycle even with `start: 10`, contradicting `plot`.
- Decision: Lines are classed by index: a major every round(major/minor) lines, accepted within 0.1 % (so typed, rounded spacings work) and placed at exact fractions of `major`, the spacing `plot` maps with. Spacings that don't nest (10 / 3) are an error, not missing lines. Log axes get `labels: "decades" | "paper"`; a given `start` defaults to decades (`start`, `start`×10, …, no exponent notation), otherwise paper style as before. `plot` tolerates points 0.01 % outside the rect.
- Rejected: warn and draw anyway (the report's alternative; a grid without its majors is never what was meant); SI-prefix / scientific label styles now (deferred to the round-2 synthesis with the other log-label wishes).
- Consequences: The datasheet's Figure 1 axis works as typed; log axes need no hand-made labels for decade values.

## D-024: Round-2 build plan; domain-specific features stay out
- Date: 2026-09-28
- Status: accepted
- Context: The round-2 synthesis (reports 4–10) ranked the needs and asked 6 review questions.
- Decision: Build in this order: (0) small fixes + `clip`/text `halo` keys, (1) files in: SVG and image import into the current document, specs/rows from JSON files, (2) automatic overlap/overflow warnings + stored relative placement, (3) grid cells in `repeat` + region split, then decide about tables, (4) components/anchors/callouts and style maps/legends. Warnings are automatic for touched elements. Relative placement is stored and re-applied like `fit_to`. Domain-specific features (cartography, architecture, swimlanes, comic balloon styles, dimension chains/scale bars, log label styles) are **not** part of inksmcp, not even as optional toolsets. The next field tests run after steps 0–3.
- Rejected: optional domain toolsets (they mix objectives and invite overlapping features); one-shot placement (it doesn't follow later text changes); more field tests before building (7 reports already agree on the top needs).
- Consequences: The tool list grows only with general primitives, preferably as keys on existing tools. A domain task relies on general primitives plus scripts outside the MCP (which `import` and specs files make cheap).

## D-025: Step 0 keys: `clip` copies a shape; connectors live in layers; gaps use our routing
- Date: 2026-09-28
- Status: accepted
- Context: Round-2 step 0 (D-024): the clip recipe needed Inkscape knowledge (reports 5, 8); connectors landed at the document root and label ids were hidden (9); arrowheads touched target text (6); big `repeat` responses (6); an `id_prefix` clash (5).
- Decision: `clip` (any element) takes an element id or `[x, y, w, h]` (parent coordinates). The shape is **copied** into a clipPath in the element's own coordinates (F32), so the reference stays visible (a panel frame) and the clip moves with the element afterwards. `null` removes it, and our clipPaths are replaced, not accumulated. Text `halo` / `halo_width` are the paint-order stroke that `plot`/`connect` labels already used. Connectors go into the layer both ends share, else a "Connectors" layer; the response lists layers and label ids. `start_gap` / `end_gap` switch a connector to inksmcp routing, because Inkscape re-routes native connectors on every load (F15), export included. `repeat` shortens id runs (`card-1..card-12`), rejects an `id_prefix` equal to a template id, maps `clip` to same-row elements, and takes `order: "column"`.
- Rejected: a stored clip reference that follows the reference shape (no report needed it; the copy follows the clipped element, which is what panels and crops want); Inkscape's `object-set-clip` (it consumes the reference object); keeping connectors at the root (they show up as loose elements).
- Consequences: The comic panels and map frame clip with one key. Tool list +2.0k chars (27.7k → 29.7k). Child bboxes in summarised `inspect` output are left to step 2's overflow warnings.

## D-026: Files in: an `image` element, `import_file`, and data paths
- Date: 2026-09-28
- Status: accepted
- Context: Step 1 of D-024. Report 8 could not pass 51 kB of geometry through the tools; report 7 pasted 20k chars of generated specs twice; report 6 pasted 118 rows; field test 4 (images) waits for image import.
- Decision: (1) `image` is an element type (so `repeat` can stamp photo cards): `href` is a path stored as a `file:///` URI, or a data URI with `embed: true` (F33). Missing sizes come from the PNG/JPEG/GIF header at 96 dpi, keeping the ratio. `object_fit` contain/cover/fill maps to `preserveAspectRatio` (F34). The source path is kept in `inksmcp:src`. (2) The `import_file` tool: an SVG becomes one group scaled from the file's units to ours (or to width/height), top-left at `at`. Its layers become labelled groups and its defs join ours. Clashing ids are renamed `<group>-<id>` and every reference follows (url(#), href, connector ends, our fit/route/clip/label metadata). An image file becomes an image element. (3) `add_elements` `elements_path` (JSON list or `{elements, defaults}`) and `repeat` `rows_path` (JSON or CSV with numbers parsed). Relative paths start at the document's folder. Responses from files shorten id runs.
- Rejected: Pillow as a dependency (headers are 30 lines); Inkscape's own import (not available headless as a file-into-document action); linking plain paths (F33); remote URLs (no downloads from a drawing tool).
- Consequences: E26: a map with 51 kB of geometry, 40 CSV labels, a clip and a photo inset takes 7 calls and 1.1k request chars. Linked images break if the file moves; `embed` makes a self-contained SVG. Tool list 29.7k → 32.3k chars (23 tools).

## D-027: Automatic overlap warnings; stored `place`; layout anchors
- Date: 2026-09-28
- Status: accepted
- Context: Step 2 of D-024. In 6 of 7 round-2 reports, overlaps were found by zooming in. Report 4's only rework came from hand-picked baselines; report 10 fixed plot frames by hand with 9 transforms. The review chose automatic warnings and let us decide between stored and one-shot placement.
- Decision: (1) Editing tools (add, update, repeat, import_file, connect, plot, align, layout) check the elements they touched, and everything inside them, against the whole page. Three findings: text overlaps text; text crosses the edge of a rect/circle/ellipse/image (inside is fine); a text **without a halo** is crossed by a stroked line/outline (curves are skipped). Exempt: page backgrounds, `grid` lines, a connector's own label, a label that lies within a stroke at least as thick as the text (a value on a bar). **Stacks** are three or more elements sharing a box corner, box centre or text anchor, i.e. dropped on one spot to be arranged later, the workflow we recommend. They are reported once, not pair by pair. At most 12 findings are listed plus a count. (2) `place: {below|above|left_of|right_of: id, gap, align}` is **stored** (`inksmcp:place`). `Engine.settle` re-applies place and `fit_to` in **one** dependency order after add/update/repeat, measuring again only when a later constraint depends on something that moved. After align/layout, only constraints whose *reference* moved are re-applied (`deps_only`), so an explicit move of the placed element wins. This amends D-020: fitted rects now also follow moves of their targets, and it costs a measurement only when such dependents exist. An element can't have both `place` and `fit_to`. (3) `layout` items may be `{"ids": [...], "anchor": id}`: arranged by the anchor's box, the rest moves along.
- Rejected: warnings only on request (the review chose automatic); one-shot placement (it doesn't follow later edits, which were report 4's pain); per-pair reporting of stacks (E20 flowchart: 12+ lines of noise per call before the fix); checking curves (flattening can come later if needed).
- Consequences: E27 names exactly the real collisions (map labels, a label on a road, a label across a box edge) and nothing in a clean flowchart. E20 responses: +320 chars on the flowchart (two stack notes), none elsewhere; the suite runs ~4 s longer. Tool list 32.3k → 32.9k chars.

## D-028: Grid cells and `split`; no table element (yet)
- Date: 2026-09-28
- Status: accepted
- Context: Step 3 of D-024. Positions on irregular grids were computed by scripts (report 6: periodic table) or typed per node (report 9: lanes and columns). Panel rects were typed three times (report 5). Four reports asked for a table element.
- Decision: `repeat` `cell: ["col", "row"]` places each row by its own 1-based column/row values (gaps and fractions allowed); the template is drawn for cell (1, 1) and `step` is the pitch. The `split` tool divides a region ("page", an element's measured box, or a rect; margin) into rows of column ratios with gutters and height ratios, and creates named cell rects (invisible unless styled) that the other tools target by id. **No `table` element**: E28 built the floor plan's area statement (header, 6 rows, right-aligned numbers, total row with a heavier rule) in 3 calls from `split` + `repeat`, typing only the column edges `split` returned, a row pitch and a baseline. The recipe is in the `split` description.
- Rejected: a separate `grid` of cells in `repeat` with its own origin (the template position already is the origin); a `table` element now (it would duplicate `repeat` and add ~2k chars to the tool list; revisit if field tests still build tables awkwardly); split cells without elements (the agent would type the coordinates again).
- Consequences: The comic page grid (6 mixed-width panels, one clipped character, a caption aligned in its panel) takes 4 calls with no hand geometry. Tool list 32.9k → 35.7k chars (24 tools).

## D-029: Overlap checks skip what an opaque shape hides; one line per text
- Date: 2026-09-28
- Status: accepted
- Context: The first field test after D-027 (comic page 2) got 15 warnings like "text 'b1_t' crosses the edge of 'stripe-9'", and the Nutmeg panel 5 more (bricks, a bush). Every one was a text on its own opaque balloon or caption box drawn over a patterned background: nothing under the box can collide with the text. The list is capped at 12, so noise can hide a real finding.
- Decision: (1) A pair (text, other) is skipped when an opaque shape painted **above the other element** covers the whole text box. Opaque: a rect (rounded corners checked), circle, ellipse, polygon or closed straight path with a plain fill, no fill-opacity or opacity below 1 on it or its ancestors, no url() paint, clip or mask. Covering is tested in the shape's own coordinates, so rotated and scaled shapes count. Paint order = document order. (2) Edge and line findings are grouped per text ("crosses the edges of 7 shapes: 'balloon', 'stripe-3', ... (+4 more)"), topmost shapes named first, so an uncovered text on a pattern is one line.
- Rejected: a `checks: false` flag on layers or elements (the report's fallback: one more key in every schema, and the agent must remember it); skipping by layer (a layer above says nothing about coverage); treating images as opaque (PNGs often have transparency).
- Consequences: E29 over nine finished pages: the two comics go from 15 and 5 warnings to 0; the map, poster and Tamil findings stay (heat pump: one label now correctly hidden under the valve shape drawn over a zone edge). A text under an opaque shape (itself hidden) is not reported yet.

## D-030: Normalise foreign files on open; find, use and def pruning for editing
- Date: 2026-09-28
- Status: accepted
- Context: Field report 11 was the first test on files this server didn't write (Inkscape's own samples). It found a .svgz that could not be opened (with an empty error), a page that `page_fit` made non-uniform, colours invisible in `inspect`, ids that differed between `document_open` and `import_file`, root paint inherited by new elements and lost on import, symbols that could only be placed by importing a whole library, and 200 unused symbols left behind. E30 showed the page problem is general (F35): any file whose viewBox doesn't match its page was measured wrongly.
- Decision: (1) `document_open` (and `import_file`, which now reads through it) **normalises** the file so every tool's assumption holds, without changing how it renders: viewBox origin 0,0 and one uniform scale (% sizes read as Inkscape reads them; the letterbox offset, origin or `none` stretch moves onto the top-level transforms); root fill/stroke/font properties move onto the top-level elements and defs (S12). The response's `notes` says what changed, and which ids were assigned. (2) .svgz opens and saves (by extension); `sodipodi:docname` is the saved name. (3) Every unexpected exception reaches the agent as `Unexpected <Type>: <message>`. (4) `inspect` shows computed fill/stroke (style, attributes, inherited), `use` targets and flowed text; `inspect find` returns a flat list by type, colour (any notation), text, href or id prefix, and lists symbols with titles. (5) A `use` element type: `href` a local id or `library.svg#symbol`, which copies the symbol and its dependencies into defs once, with the library's root paint. (6) Deleting elements removes the defs only they referenced (transitively); defs that were already unused are left alone. (7) `place` reports the placed box, not the move; the `defaults` error names a `type` key.
- Rejected: fixing the coordinate model to support offsets and non-uniform scales everywhere (every tool and export would need it; normalising touches one place); leaving root paint alone and warning (the agent would have to add `stroke: none` to every element); a `vacuum_defs` option (pruning at delete time needs no call and never touches defs the author kept on purpose); converting flowRoot ourselves (legacy only; listed and movable is enough, F36).
- Consequences: Files saved after editing differ from the original in the root attributes and top-level transforms, but render the same. Tool list +1.1k chars (`find`, `use`, notes). The tiger's eyes are one `find` call; a legend from a symbol library is one `add_elements` (or `repeat`) call.
