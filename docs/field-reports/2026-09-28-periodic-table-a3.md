# A3 landscape poster: The Periodic Table of the Elements (secondary school)
- Date / client / model: 2026-09-28 / Claude Code (desktop app, Code tab) / Claude Opus 5.5.
  Written by the session that also works on inksmcp (same caveat as reports 4–5).
- Result files: `out/periodic-table-a3.svg`, `out/periodic-table-a3.pdf` (text to path, 820 kB),
  `out/periodic-table-a3.png` (300 dpi, background `#fbfaf6`, 1.67 MB)
- Tool calls (approx.) and time: 17 inkscape tool calls (1 document_create, 6 repeat [1 rejected:
  reserved key], 1 add_elements, 1 connect, 1 layout, 1 update_elements, 1 align, 2 render_preview,
  1 document_save, 2 export). Plus 1 shell call (a Python script that builds the 118 data rows with
  positions and colours) and 1 file read to copy the rows into the call. 2 editing calls used
  `preview: true`. About 20 minutes. No errors apart from the rejected call.

Task prompt (written first): an A3 landscape poster for students aged 11–16. All 118 elements in the
standard 18-column layout, with the f-block in two rows below, group numbers 1–18 and period
numbers 1–7. Each cell has the atomic number, a big symbol, the name and the relative atomic mass
([ ] for the most stable isotope). Cell colour = family (11 families); symbol colour = state at room
temperature (black solid, blue liquid, red gas, grey unknown). The empty top-centre area holds a
labelled 2× "how to read a cell" key (carbon) and the family legend. The bottom has 4 fun-fact cards.

Result: every item in the prompt is on the page. Title band (navy) with a columns/rows explainer;
118 cells (20.5 × 21 mm on a 21.5 × 22 mm pitch); "57–71" / "89–103" placeholder cells;
Lanthanides/Actinides row labels; the key with 4 annotation lines; the state-colour line; an
11-swatch legend; 4 fact cards; a source note in the footer. Font: Segoe UI.

## What worked well
- **One `repeat` call drew the whole table: 118 rows × 5 elements = 590 elements**, correct on the
  first render. The recipe from the comic (`step: [0, 0]`, group `transform: "translate({x},{y})"`)
  works as "place each row at data coordinates". Per-row `"fill": "{fill}"` and `"fill": "{sc}"`
  handled the family and state colours.
- **No shell crash** at 590 elements (compare report 5's intermittent crash at 37). One data point,
  but a useful one.
- **`{n}` as the row number**: the period labels 1–7 need no data (`rows: [{}, …]`, `text: "{n}"`).
- **`align` and `connect` handle elements inside a transformed group.** The key is
  `translate(68,47) scale(2)`. `connect` (`from_side: left`, `to_side: right`) attached to the scaled
  parts, and `align vertical: middle` with `to: "key_num"` levelled each label with its part. The
  connectors followed the moves.
- **`repeat` with `columns: 2`** made the legend, and text `width` inside a `repeat` template wrapped
  all 4 fact bodies (`wrapped_lines` reported 2 lines each).
- `layout` spaced the four state words by their measured widths.

## What was awkward (agent had to compute, retry, or work around)
- **Table positions were computed outside the tools.** Group/period → (x, y) needs the periodic
  table's shape (period starts, the f-block gap). I wrote a 40-line script for it. Even if an agent
  knows a cell's (column, row), `repeat` only offers a sequential grid, so irregular grids (gaps)
  need explicit coordinates.
- **Category → colour was baked into every row.** 118 rows each carry `fill` and `sc` hex values.
  The legend is another `repeat` that repeats the same 11 colours. Nothing ties the legend to the
  cells, so a colour change means editing both.
- **Group-number heights by hand**: each label sits 2.5 mm above the top cell of its column
  (y = 38.5 / 60.5 / 104.5). There's no "place above element `el-5`".
- **Layout collision found only in the zoomed preview**: I put the state line at y 103, where the
  group labels 3–12 sit (104.5). The first full-page preview was too small to show it. That's the
  third report in a row where overlaps are found by eye.
- **Connector arrowheads touch the target text** ("Carbon", "12.011"). There's no gap/padding option
  at the end of a connector.
- **Fact cards have a fixed height** (33 mm for 2-line bodies, so there's spare space). With `fit_to` each card
  would get its own height. The need here is "same height for the row, from the tallest".
- **Reserved key**: a row key `n` is rejected (`rows[0]: ['n'] are reserved (row index / number)`).
  The message is clear and it turned into a shortcut, but the tool description doesn't mention it.
- **Big responses**: the 118-row `repeat` returned every id for each of the 6 template names
  (~8 k characters of `cell-1 … mass-118`) that I never needed. A range form (`cell-1..118`) would do.

## Missing tools or options
- **Grid-cell placement in `repeat`**: `grid: {"origin": [20, 41], "pitch": [21.5, 22]}` + per-row
  `col`/`row` keys (1-based, gaps allowed). It covers periodic tables, calendars, timetables,
  seating plans and bingo cards.
- **Style maps / palettes**: `"maps": {"fill": {"key": "cat", "values": {"ak": "#f7a6a6", …}}}` (or a
  placeholder like `{cat|fill}`). A legend could then be generated from the same map.
- **Place relative to an element**: `above: "el-5", gap: 2.5` (again: see report 4's "stacking").
- **Connector end gap**: `end_gap` / `start_gap` in user units.
- **Equal-height rows of cards**: `fit_to` with `fit: "height"` over a set, sized to the tallest.
- **Compact `repeat` response** (ranges, or ids only on request).
- **Overlap warnings** (also reports 4, 5).

## Bugs / surprising behaviour (with the exact call and response)
None. Minor: the family legend's 11th row sits alone in column 1. That's expected from a row-wise
grid. A `order: "column"` option would give 6 + 5 columns.

## Content caveat
Masses and families come from the model's knowledge, not a checked source. Family conventions differ
between textbooks (Po as post-transition metal, At as halogen, Rf–Hs as transition metals, Mt–Og as
unknown). Hs is given as [269] (some tables use [277]). A teacher should check these before printing.

## Suggestions
- Most useful for data-driven posters: **grid-cell placement + style maps in `repeat`**. This
  poster would then need no external script: the rows could be (symbol, name, mass, col, row, family).
- **Overlap warnings** now have three reports behind them; worth doing in the synthesis.
- A compact `repeat` response is cheap and helps every large stamp.

## Common or task-specific? (input for the round-2 synthesis)
| Need | Seen before? | Guess |
|---|---|---|
| Grid-cell placement (col/row with gaps) in `repeat` | Report 5 (panels by hand), report 3 (timeline positions) | Common: tables, calendars, timetables, seating plans |
| Category → style map, legend generated from it | Report 2 (legend by hand), report 3 (bar colours) | Common for any categorical data |
| Overlap/collision warnings | Reports 4, 5 | Common (3 of 3 in round 2) |
| Place relative to an element (above/below + gap) | Report 4 (stacking in cards) | Common |
| Connector end gap | Report 2 (arrow stubs, since fixed) | Common for annotated diagrams |
| Equal-height card rows | Report 3 (card heights) | Common for card grids |
| Compact `repeat` response | New (first 100+ row repeat) | Common for large stamps; cheap |
| Row-wise vs column-wise grid order | New | Minor, common |
| Periodic-table shape itself | — | Specific (belongs in the data, not the tool) |
