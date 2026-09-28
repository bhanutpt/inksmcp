# Field-test round 2: synthesis (reviewed 2026-09-28, D-024)
- Date: 2026-09-28. Inputs: the 7 round-2 reports (4 Tamil poster … 10 datasheet), their
  "Common or task-specific?" tables, the open items left from round 1 (reports 1–3) and the Phase 3 list.
- Method (D-021): merge the needs into themes, count how many reports ran into each, estimate the
  rework it caused (calls, redo cycles, external script, tokens), and separate core needs from
  domain-specific ones. Then propose an order. **Nothing here is built yet.** Each theme ends with the
  design questions to settle in review, and each item then goes experiment → test → code as usual.
- The three bugs the reports found are already fixed (D-022, D-023, F30), so they don't appear below.

## Round 2 at a glance

| # | Task | Calls | Outside the tools | Rework caused by |
|---|---|---|---|---|
| 4 | Tamil alphabet A3 poster | 13 | — | guessed in-card baselines → 24-item fix; one over-wide glyph |
| 5 | Comic page (6 panels) | 18 | starburst one-liner | hand-computed balloon tails and panel geometry; shell crash (fixed) |
| 6 | Periodic table A3 | 17 | 40-line position script | label collision found by zooming |
| 7 | 2 BHK floor plan A4 | 16 | 150-line geometry script, 20 k chars pasted | label/furniture collision; walls, doors, dimensions scripted |
| 8 | OSM route map A3 | 18 | ~200-line GIS script | 51 kB geometry could not pass through the tools; ~50 labels placed by reasoning |
| 9 | Swimlane flowchart A4 | 18 | none | grid positions typed per node; labels crowding short arrows |
| 10 | Datasheet, 4 plots A4 | ~41 | synthetic data | 2 grid bugs (fixed); plot frames aligned by hand (9 transforms); legend from 3 tools |

Every task was finished, with no tool errors apart from the bugs and a few mistakes by the agent. Calls cluster
at 13–18. The extra cost is in **external scripts** (4 of 7), in **find-by-eye-then-fix loops**, and,
for data-heavy work, in **tokens**.

## What already works (keep it, and document it better)
- **`repeat` is the general-purpose engine.** It was used as a character component system (5), cartographic
  symboliser (8), node factory (9), table and scale bar builder (6, 7, 8) and legend (10). The pattern is a group
  `translate({x},{y})` + placeholders in geometry *and* style. Three reports found it on their own; the
  tool description doesn't teach it.
- **`fit_to`** gave badges, shields, balloons and condition boxes (5, 8, 10). **`connect`** routed a full
  flowchart with no scripts (9). **Scaled groups** gave real-world units (7). **Path operations**
  gave clean poché walls (7).
- **Clipping via `run_actions object-set-clip`** worked in two tasks (5, 8), but only because the first
  agent worked out the recipe.

## Needs by theme

✓ = the report asked for it or worked around its absence. Round 1 = reports 1–3.

| Theme | 4 | 5 | 6 | 7 | 8 | 9 | 10 | Round 1 | Reports | Rework | Class |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A. Overlap / overflow warnings | ✓ | | ✓ | ✓ | ✓ | ✓ | ✓ | — | **6 / 7** | High: a zoom + fix each time; report 10 rebuilt its labels as a legend | Core |
| B. Place relative to measured elements (below / right_of / on + gap; section stacking; layout by anchor) | ✓ | ✓ | ✓ | ✓ | | ✓ | ✓ | 3 | **6 / 7** | High: report 4's only rework; title blocks; 9 hand transforms in report 10 | Core |
| C. Data through files (import SVG into a doc; specs/rows from a file) | | (✓) | ✓ | ✓ | ✓ | | | — | 3–4 / 7 | Very high in tokens; **decides whether data-heavy tasks work at all** (8) | Core |
| D. Grid cells / region split / tables | (✓) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 3 | **6 / 7** | Medium: positions typed or scripted; tables built from `repeat` each time | Core |
| E. Components: update all instances, anchors, callout tails | ✓ | ✓ | | | ✓ | | | 2, 3 | 3 / 7 | Medium: 24-item and 4-item repeat fixes; 8 hand-computed tails | Core |
| F. Legends and category → style maps | | | ✓ | | ✓ | ✓ | ✓ | 2 | 4 / 7 | Medium: 29 hand-placed legend elements (8); colours duplicated (6) | Core |
| G. Cheap element keys: `clip`, text `halo` | | ✓ | | | ✓ | | | (plot/connect have halo) | 2 / 7 | Low per use, but needs Inkscape knowledge | Core |
| H. Shapes: star / regular polygon, flowchart presets, callout | | ✓ | | | | ✓ | | 2 (block arrow, done) | 2 / 7 | Low–medium: polygons by script or by hand | Core-ish |
| I. Text: styled runs, shrink-to-fit, font check | ✓ | | | | | | | 2 (lists) | 1–2 / 7 | Low–medium | Core-ish |
| J. Drawing to scale: dimension, scale bar, paper-space strokes | | | | ✓ | ✓ | | | 1 | 2 / 7 | High inside the domain (7: most error-prone script part) | Technical |
| K. Charts: figure = one group, plot legend, log label styles, bar series | | | | | | | ✓ | 3 (bars) | 1 / 7 | High for multi-chart pages (41 calls) | Charts |
| Domain: geo layer, walls/doors, swimlanes, balloon styles | | ✓ | | ✓ | ✓ | ✓ | | — | 1 each | High inside their domain | Domain |

## Proposal, ranked

The ranking is by frequency × rework, with cheap items first when they don't cost much. Every new tool adds to the
≈ 6.3k-token tool list (E20), so **keys on existing tools come before new tools**.

### 0. Small fixes (one batch, no design needed)
Each of these was asked for once and is cheap:
- `repeat`: compact response (id ranges such as `cell-1..118`, report 6); warn when `id_prefix` equals a
  template id (5); document the reserved `n` key (6); `order: "column"` for grids (6).
- `connect`: return label ids; put connectors in a layer (the endpoints' layer, or `layer`); `end_gap` / `start_gap` (6, 9).
- Descriptions: the `repeat` component pattern, the clip recipe (until G), when to use `text_metrics: visual`
  (non-Latin scripts, paragraphs; report 4), and what coordinates mean when you add into a transformed layer (10).
- `inspect`: child bboxes inside summarised repeat groups (4).

### 1. Data through files (C): the feasibility gate
- `import` (or `add_elements` `from`): an SVG file or fragment into the current document as a group/layer,
  with `at` / `scale`, ids made unique. `add_elements` `specs_path` and `repeat` `rows_path`: JSON on disk
  goes straight to the tool, so the model never reads it.
- Why first: it's cheap, and report 8 shows that without it data-heavy maps, plans and tables either don't fit
  or cost more tokens than the rest of the task. It is also the base for asset libraries (the comic direction) and image import (Phase 3).
- Review: (a) import only SVG, or also images now (field test 4 is waiting for that)? (b) relative paths
  from the document's folder? (c) how to rename ids on a clash (`<prefix>-<id>`)?

### 2. Layout checks (A): 6 of 7 reports
- Warnings in editing responses, limited to the touched elements: text overlapping text; text crossing a
  shape's edge (partly in, partly out); text wider than its `fit_to`/card rect or the rect its template sits in;
  connector label longer than its segment. Plus a `check` option on `render_preview` / `inspect` for the whole page.
- Review: (a) automatic, or only on request (cost: one measurement, which most calls already make)?
  (b) which pairs count? Text over a background is intended, while text over a line or the edge of a shape is usually not.
  (c) suggest a free position (N/NE/E…) or only report?

### 3. Relative placement (B): 6 of 7 reports
- Element keys resolved after wrapping, using measured bboxes: `below` / `above` / `left_of` / `right_of` / `on`
  (bottom on top of another) + `gap`, and `align_with` for the cross axis. They work inside `repeat` templates
  (local names), so in-card stacking follows the real glyph extents of any script (4).
- `layout` `anchor`: per item, the member used for alignment (plot frame, not label bbox; 10).
- Section stacking (4, 7) is `layout direction: column` over groups once those exist. Check whether that's enough
  before building anything more.
- Review: one-shot placement, or stored like `fit_to` so it re-applies when the reference text changes?
  (Recommendation: stored, the same mechanism as `fit_to` with dependency order. Report 4's pain was
  a fix after stamping.)

### 4. Grid cells, region split, tables (D)
- `repeat` `grid: {"origin", "pitch"}` + per-row `col`/`row` (gaps allowed): periodic tables, calendars,
  timetables, flowchart lanes, seating plans (6, 9).
- Region split: rows with ratios and a gutter inside a rect → named rects (comic panels, dashboard tiles,
  poster columns; 5, 3). It could create background/frame/clip rects in one go.
- Table: after the two above, decide whether a `table` element is still needed or a documented `repeat` +
  grid recipe covers it (4 reports built tables with `repeat` successfully).

### 5. Components (E)
- Update all instances of a template name (`{"template": "sound", ...}`): the fix-after-preview loop in 4 and 5.
- Stored templates on `repeat` groups, so one more instance can be added later.
- Named anchors in templates (`"anchors": {"mouth": [0, -47]}`), addressable as `mia-2.mouth`. Then a
  **callout** element with `tail_to` an id/anchor/point (comic balloons, infographic annotations, map callouts).
- Review: build on `repeat` groups (poses can vary) or on SVG `<symbol>`/`<use>` clones (true components, but
  poses can't vary)? Experiment both before deciding.

### 6. Legends and style maps (F)
- Category → style maps in `repeat` (`"maps": {"fill": {"key": "cat", "values": {...}}}`), and a legend built from a
  map or from `plot` series (symbol + label rows, boxed). This covers 6, 8, 9 and 10.

### 7. Cheap keys (G): can ride along with 0 or 1
- `clip`: an element id or a rect, on any element or group (5, 8; image import will need it).
- Text `halo` / `halo_width`, as `plot` and `connect` labels already have (8; comic and map labels).

### Later, when a task needs them (H, I, J, K)
- Shapes: `star` / regular polygon (bursts, badges, seals), flowchart presets with centred wrapped text.
- Text: styled runs (split on grapheme clusters for complex scripts), `max_width` shrink-to-fit, font availability check.
- Drawing to scale: `dimension` element (chains, ticks, extension lines), scale bar, non-scaling strokes.
- Charts: figure = one group (grid + labels + data), `plot` legend (via 6), log label styles (SI, scientific), bar series.

### Domain modules: not in the core tool list
Geo layer (projection, simplification, ring assembly), walls + doors/windows, swimlane containers, comic balloon
styles, periodic-table data. Each is high value inside its domain and unused outside it. Proposal: optional
toolsets switched on by configuration, so the default tool list doesn't grow.

## Proposed order
1. Small fixes (0) + cheap keys (7).
2. Files in (1): then run **field test 4 (images)** as the Phase 3 plan intended, if image import is included.
3. Layout checks (2) and relative placement (3): they share the measurement pass, so design them together.
4. Grid cells + region split (4), then decide about tables.
5. Components and callouts (5), legends and style maps (6).
6. Re-run the E20 benchmark plus two round-2 tasks (the Tamil poster and the datasheet are the most sensitive
   to B and D) to measure the gain. Then decide on the "later" list.

## Questions for review
1. Is the order right? In particular: files before checks, even though checks come up more often (C is a feasibility gate, A is quality)?
2. Warnings (A): automatic in every editing response, or on request?
3. Relative placement (B): stored and re-applied like `fit_to`, or one-shot?
4. Image import: in step 2, or after the layout work?
5. Domain modules: optional toolsets now, or leave them out entirely for the moment?
6. More field tests before building (org chart, certificate, worksheet are still on the list), or build steps 1–3 first and test after?

## Review outcome (2026-09-28, D-024)
1. **Order: accepted as proposed** (small fixes + cheap keys → files in → checks + placement → grid cells → components / style maps).
2. **Warnings: automatic** in every editing response, for the touched elements.
3. **Relative placement: stored**, re-applied like `fit_to` (the reference text changes → the dependent element follows). Report 4's rework came from a fix after stamping, which a one-shot placement would not have followed.
4. **Image import: in step 2**, together with SVG import. It shares the mechanism (path, `at`/size, ids) and uses the `clip` key from step 0, and it unblocks field test 4.
5. **Domain-specific features are out of scope for this MCP**: not optional toolsets, not at all. That covers the geo layer, walls/doors, swimlanes, comic balloon styles and domain data, and also the drawing-to-scale vocabulary (dimension chains, scale bars) and log label styles. The server stays general-purpose, so objectives don't mix and features don't overlap. A domain need is met by a general primitive (`repeat`, `import`, relative placement), or by a script outside.
6. **Field tests after the fixes**: build steps 0–3, then run the next tasks (org chart, certificate, worksheet, an image flyer).
