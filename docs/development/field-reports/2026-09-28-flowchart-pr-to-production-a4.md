# A4 swimlane flowchart: From Pull Request to Production
- Date / client / model: 2026-09-28 / Claude Code (desktop app, Code tab) / Claude Opus 5.5.
  Written by the session that also works on inksmcp (same caveat as reports 4–8).
- Result files: `out/flowchart-pr-to-production-a4.svg`, `.pdf` (text to path, 139 kB), `.png` (300 dpi, 360 kB)
- Tool calls (approx.) and time: 18 inkscape tool calls (1 document_create, 2 add_elements, 3 repeat, 1 connect,
  2 inspect [1 errored: I guessed a layer name], 2 update_elements, 2 layout, 2 render_preview, 1 document_save,
  2 export). 5 editing calls used `preview: true`. **No external scripts or computation files**: the first
  round-2 task done entirely through the MCP. About 15 minutes.

Task prompt: A4 landscape, 4 horizontal swimlanes (Developer · CI Pipeline · Code Reviewer · Release)
with a coloured header column. Standard symbols (terminator, process, decision diamond), orthogonal
arrows with Yes/No labels, two loops back to "Push new commits", a failure branch (roll back → fix in a
new PR), a title, a shape legend and a footer note.

Result: every item in the prompt is on the page. 17 nodes (11 process, 3 decisions, 3 terminators) and 18
connectors, 7 of them labelled. Green = yes / happy path, red = no / failure. One loop runs over the top of
the Developer lane through two waypoints. No crossings, and no connector passes through a node.

## What worked well
- **`connect` did all the routing**: 18 connections in one call with only `from_side`/`to_side`
  (plus `via` for one loop). Elbows came out orthogonal and clean. Diamond vertices work as attachment
  points because a diamond's bbox side midpoints are its vertices. Arrowheads take the stroke colour;
  labels take `label_color`, `font_weight` and `label_side`.
- **Connectors follow moves and re-place their labels.** Moving 5 node groups with `update_elements
  transform` re-routed the attached arrows and re-centred the "Yes"/"No" labels on the longer segments.
  That overrode my manual label fix (correctly).
- **Nodes via `repeat` + group `translate({x},{y})`**: a shape drawn once around a local origin, text
  centred with `vertical_anchor: middle` and wrapped with `width` (`wrapped_lines` shows which labels took
  2 lines). This is the third task using this pattern (characters, map symbols, flowchart nodes).
- **Legend with two `layout` calls**: an interleaved row placed each text next to its symbol (gap 1.6).
  A second row of `[symbol, text]` pairs (gap 5, `to: page`, `horizontal: right`, `margin: 10`) spaced and
  right-aligned the pairs. The symbols were created at the origin without computing any coordinates.
- `connect` supports `marker_end: "arrow"` on legend lines, so the legend arrows match the chart.

## What was awkward (agent had to compute, retry, or work around)
- **Grid positions by hand**: 7 columns (x = 42 + 33·k) and lane centre lines (51 / 91 / 129 / 163 / 186),
  typed into every node row. The nodes sit on a grid, but `repeat` can't place rows by (column, lane).
- **No flowchart shapes**: the diamond is a polygon with hand-picked points; the terminator is a rect with
  `rx = h/2`. No document/data/database shapes.
- **Short-segment labels crowded their arrows**: two decisions were only 4 mm from their targets, and
  the "No"/"Yes" labels touched the arrowhead and box. `connect` gave no warning. Fixed by moving nodes apart.
- **Connectors land at the document root**, not in a layer (inspect listed them as "loose elements not in a
  layer/group" with the background). The `connect` response lists connector ids but not their **label ids**
  (`connector20_label`), so I needed an `inspect` (and guessed a non-existent "Connectors" layer first).
- **Rotated lane titles**: `rotate(-90 x y)` + `text_anchor: middle` centres them along the lane, but centring
  across the header column's width was done by eye (the baseline sits to the right of the glyphs).

## Missing tools or options
- **Flowchart shape presets**: `{"type": "shape", "shape": "decision|terminator|process|document|data|database|
  predefined", "x", "y", "width", "height", "text"}`, with the text wrapped and centred inside.
- **Grid-cell placement** for `repeat`/`add_elements`: `grid: {origin, pitch}` + `col`/`row` per item
  (report 6 needed the same for the periodic table).
- **Connector defaults**: put connectors in a named layer by default (or in the endpoints' layer), and
  return the label ids in the response.
- **Label fit check** on `connect`: warn when a label is longer than its segment or overlaps a node.
- **Place relative to an element** (`right_of: "lg_term", gap: 1.6`): the legend needed a two-call trick.
- **Swimlane container** (optional, diagram-specific): lanes with a header band and a centred rotated title.

## Bugs / surprising behaviour (with the exact call and response)
None. The one error was mine: `inspect(layer="Connectors")` → `No layer named 'Connectors'.`

## Suggestions
- `connect` is now strong enough that flowcharts are easy. The cheap improvements are **label ids in the
  response**, **connectors in a layer**, and **a label-fit warning**.
- **Shape presets** would remove the last hand geometry from flowcharts (and help org charts, BPMN-lite and
  UML-lite diagrams).

## Common or task-specific? (input for the round-2 synthesis)
| Need | Seen before? | Guess |
|---|---|---|
| Grid-cell placement (col/row) | Report 6 (periodic table), report 5 (panels) | Common |
| Place relative to an element (right_of/below + gap) | Reports 4, 6, 7 | Common |
| Overlap/fit warnings (here: connector labels) | Reports 4–8 | Common (6 of 6) |
| Flowchart / diagram shape presets | Report 2 (block arrows → `arrow` element) | Common for diagrams |
| Connectors in a layer + label ids in response | New | Small fix; common for diagrams |
| Swimlane container | New | Specific (process diagrams) |
