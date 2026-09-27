# A4 landscape technical poster: "How a Heat Pump Works"
- Date / client / model: 2026-09-27 / Claude Code (desktop app, Code tab) / Claude Opus 5.5
- Result files: `out/heat-pump-poster.png` (300 dpi, 3508 x 2480 px, white background, 623 kB),
  `out/heat-pump-poster.pdf` (66 kB), `out/heat-pump-poster.svg`
- Tool calls (approx.) and time: 31 inkscape tool calls (1 document_create, 3 add_elements,
  2 connect, 1 grid, 4 update_elements, 1 delete_elements, 1 move_to_layer, 1 z_order, 1 inspect,
  2 document_save, 2 export, 12 render_preview), plus 1 ToolSearch and 4 shell calls (read the
  template, grep a debug save to diagnose a text bug, check PNG size / PDF header). About 20 minutes.

Result: a 297 x 210 mm document (mm user units). Left: the refrigerant loop on two tinted zones
(INDOOR pink `#fde3e0`, OUTDOOR blue `#e3eefb`). The condenser (top) and evaporator (bottom) are
rects, the compressor is a circle and the expansion valve is a diamond; both straddle the zone
boundary. Six connectors: red `#c62828` on the high-pressure side, blue `#1565c0` on the
low-pressure side. Each leg has a two-line state label ("hot gas / high pressure", ...). Block
arrows show heat leaving the condenser and entering the evaporator. Below: a legend box. Right:
"How it works" in 4 numbered steps, a COP definition callout, and a COP vs outdoor temperature
chart (-15..15 °C, COP 1..5, 7 made-up points from 2.1 to 4.7, with a "COP 3.2 at 0 °C" note).

## What worked well
- **`grid` made the chart axes almost free.** One call with `x: {major: 14, minor: 7,
  label_start: -15, label_step: 5}`, `y: {major: 15, minor: 7.5, label_start: 1, label_step: 1}`
  drew the frame, major and minor gridlines and 12 measured tick labels in the right places.
  I only had to choose mm-per-unit so that the steps came out as whole numbers.
- **`connect` with `routing: "elbow"`** routed compressor → condenser (up, then left into the
  right edge) and evaporator → compressor (right, then up) exactly as a textbook diagram would.
  The arrowheads come out the stroke colour.
- **`defaults`** (`font_family`, `font_size`, `fill`, `layer`) kept the 28-element text batch and
  the 8 chart points short. Per-element keys correctly override the defaults.
- **Layers by name** in the element spec, plus `move_to_layer` / `z_order back`, sorted out stacking
  (data line under the point markers, both above the grid) in 2 calls.
- **`render_preview` with `region`** was the main QA tool. Zooming to an 8 x 8 mm area showed
  connector-corner notches and arrow-tip stubs that are invisible at page size.
- **`delete_elements` also removes connector labels** (`flow_comp_cond_label`, ...). The response
  lists them, so nothing was left orphaned.
- The export was right first time: `dpi: 300, background: "#ffffff"` → 3508 x 2480 px. The PDF
  export needed only `path`.

## What was awkward (agent had to compute, retry, or work around)
- **Multi-line text renders with a doubled first gap** (see Bugs), so every paragraph became
  one `text` element per line with baselines computed by hand (43, 47, 52.5, 56.5, ...).
  That meant 8 elements for the steps, 3 for the COP note, 2 for the valve label and 8 for the
  connector state labels. Wrapping was also manual: I guessed about 55 characters per 100 mm line
  at 3 mm Arial, because there is no width/wrap option.
- **Elbow connectors cannot be told which side to leave or enter.** For condenser → expansion
  valve the router went *down* from the condenser and *then* left. Valve → evaporator went right
  and then down along the same y = 90 segment, so the red and blue legs overlapped (visible in
  the first preview). Workaround: two invisible waypoint circles (`r: 0.01, fill: none`) at
  (34, 54) and (34, 126), with the left side of the loop built from 4 straight connectors
  (`arrow: "none"` on the first leg of each pair). I had to compute the corner coordinates.
- **Split connectors leave a notch at the corner** (butt caps meeting at 90°). The fix was
  `stroke_linecap: "square"` on the non-arrow legs only; on the arrow legs a square cap sticks out
  past the arrowhead into the target shape. That took 2 update calls and 3 zoomed previews.
- **Connector `label` was unusable here.** The label sits on the path midpoint, which falls on
  the elbow near its corner, so the line runs *through* the text. The white halo only covers the
  glyph outlines, so the line shows between letters, and white looks wrong on a tinted zone. The
  label also ignores the document font (it rendered in a different sans than my Arial). I
  deleted all 4 connectors and placed my own labels beside the vertical legs.
- **Block arrows (heat in / heat out, legend swatches) were hand-computed 7-point polygons**:
  `[[cx-1,yb],[cx+1,yb],[cx+1,yt+3],[cx+2.5,yt+3],[cx,yt],[cx-2.5,yt+3],[cx-1,yt+3]]` × 8. There is
  no arrow shape and no `marker-end` on plain lines/paths. The two legend arrows touched at first
  and needed another update.
- **Chart data → coordinates was manual**: `x = 197 + (T + 15) * 2.8`, `y = 186 - (COP - 1) * 15`
  for 7 points, then 7 circles and a polyline. `grid` knows this mapping but doesn't expose it.
- The rotated y-axis title needed a hand-written `transform: "rotate(-90 187 156)"`.

## Missing tools or options
- **Data plotting on a grid:** something like `plot(grid=<id_prefix>, series=[{points: [[T, COP],
  ...], marker: "circle", stroke: ...}])` that uses the grid's data→user mapping. Axis titles
  (`x_title`, `y_title` with rotation) would also fit on `grid`.
- **Connector ports / waypoints:** `from_side` / `to_side` (`top|right|bottom|left`) or
  `via: [[x, y], ...]` on `connect`, so a loop diagram doesn't need invisible helper objects.
- **Arrowheads on plain elements:** `marker_end` / `marker_start` for `line`/`polyline`/`path`
  (reusing the connector markers), plus perhaps an `arrow` element type (block arrow from
  x1,y1 → x2,y2 with a shaft width).
- **Connector label placement:** `label_position` (`0..1` along the path, or `"segment": n`),
  `label_offset` / `label_side` so the text sits beside the line, and `font_family` (or inherit it).
- **Text wrapping:** `width` on `text` (auto line breaks, e.g. via SVG2 `inline-size` or
  flowed text), so a paragraph can be one element.

## Bugs / surprising behaviour (with the exact call and response)
1. **Multi-line text: the first line gap is about twice the others; `line_height` has no visible effect.**
   Call: `add_elements` with
   `{"type":"text","id":"cop_note","x":190,"y":92,"text":"COP (coefficient of performance) = heat delivered ÷\nelectricity used. COP 3 means 3 kWh of heat for\nevery 1 kWh of electricity.","font_size":3,"line_height":1.35,"font_family":"Arial"}`
   → `{"doc_id":"doc1","ids":[...,"cop_note",...]}`. In the preview, line 1 is followed by an empty line's
   worth of space, and lines 2→3 are normally spaced. The same happened with `how_body` (8 lines) and
   `valve_label` ("EXPANSION\nVALVE", default line height). A debug save shows the markup:
   `<text id="cop_note" x="190" y="92" style="...font-size:3px;font-family:Arial"><tspan sodipodi:role="line" x="190">COP …</tspan><tspan sodipodi:role="line" x="190" dy="1.35em">electricity …</tspan>…</text>`
   — `sodipodi:role="line"` tspans with `dy` and no `line-height` in the style. Presumably Inkscape
   re-lays out role=line tspans with its own spacing *and* applies the dy. Trying
   `update_elements [{"id":"cop_note","style":{"line-height":"1.35"}}]` → `{"updated":1}` did not change
   the render. Leading spaces used as a hanging indent were also collapsed (no `xml:space="preserve"`).
2. **Connector end stubs past the arrowhead.** At 8 x 8 mm zoom
   (`render_preview region=[30,74,8,8]`, `region=[117,50,8,8]`), each arrow connector shows a strip of
   the 1.2 mm line between the arrowhead tip and the target's edge. The tip looks blunt, and
   the stub is just visible at 300 dpi. The marker seems to be placed before the path end rather than at it.
3. `move_to_layer` puts the moved element on top of the target layer (documented), so after
   moving `cop_line` into "Chart data" it covered the point markers. That's expected, but it needed an
   extra `z_order back`. A `position: "bottom"` option would save the call.

## Suggestions
- **Single new tool that would have helped most: `plot`** — draw series (line / markers / optional
  point labels) on a grid by data values, with axis titles, reusing `grid`'s axis specs. The
  chart was the only part of the poster where every coordinate had to be computed by hand.
  Close second: side/waypoint control on `connect` (it caused 1 delete, 2 helper objects, 4
  extra connectors and 3 zoom previews).
- Fix multi-line `text` (bug 1). Until then, the tool description shouldn't advertise `'\n'`
  support. Once fixed, add a `width` option for wrapping.
- Let the connector label inherit `font_family` and sit next to the line instead of on it.
