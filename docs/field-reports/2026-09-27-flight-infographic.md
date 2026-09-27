# A3 portrait infographic: "The History of Flight, 1903–1969"
- Date / client / model: 2026-09-27 / Claude Code (desktop app, Code tab) / Claude Opus 5.5
- Result files: `out/flight-infographic.png` (300 dpi, 3508 x 4961 px, white background, 1.36 MB),
  `out/flight-infographic.pdf` (54 kB, Segoe UI / Segoe UI Bold / Georgia Bold embedded as subsets),
  `out/flight-infographic.svg`
- Tool calls (approx.) and time: 26 inkscape tool calls (1 document_create, 4 add_elements,
  5 update_elements, 1 layout, 2 align, 1 grid, 1 plot, 8 render_preview, 2 export,
  1 document_save). 3 editing calls also used `preview: true`. Plus 1 ToolSearch and 3 shell calls
  (read the template, check the PNG size and PDF header, check the PDF fonts). About 25 minutes.

Result: a 297 x 420 mm document in mm user units. At the top is a navy header (`#0f2742`) with an
orange kicker, "The History of Flight" in white Georgia Bold and "1903–1969" in orange on the same
baseline. Below them are a subtitle, a dashed flight-path flourish and an orange rule. The
timeline is a grey spine at x = 148.5 with 8 icon badges at a 29 mm pitch: a navy disc, a white
ring with an orange outline, and an icon built from basic shapes. The icons are a biplane, a
propeller, a globe with a dashed route, a straight-wing monoplane, a swept-wing jet, a dart with
Mach-cone chevrons, a tilted rocket, and the Moon with a flag. 8 cards alternate left and right.
Each has a large orange year, a bold title and a 3-line wrapped description. Next comes a panel
with a horizontal bar chart of top speeds: Wright Flyer 48, Spirit of St. Louis 214, Spitfire I
582, Bell X-1 1,127 (Mach 1.06 record run) and Concorde 2,179 km/h, on a 0–2500 axis. The page
ends with a navy footer that lists the sources.

## What worked well
- **Text `width` wrapping plus `wrapped_lines` in the response.** All 8 descriptions came back as
  `"wrapped_lines": {"desc1": 3, ...}`. After I raised the font from 3.3 to 3.5 the response still
  said 3 lines each, so I could size the cards without a preview. This replaced the manual line
  breaking described in the heat-pump report.
- **Groups with `transform` plus `parent`** turned the icons into local-coordinate drawings. I
  created `{"type": "group", "id": "icon7", "transform": "translate(148.5,252) rotate(35)"}` and
  then drew every child around (0, 0). Blades that need `rotate(120)` / `rotate(240)` took a
  per-element `transform`. The 8 icons (43 shapes) went in one `add_elements` call and needed no
  corrections.
- **`layout` row with `align: "end"`** put "1903–1969" right after the title on the *same
  baseline*, even though Georgia's old-style figures have a different bbox. It measured the title
  width for me.
- **`align` to a polyline** (`{"ids": ["name3"], "to": "polyline86", "vertical": "middle"}`)
  centred the category and value labels on the bars in one call with 10 operations.
- **`align` `as_group`** centred the three footer texts in the footer band vertically, keeping
  their relative positions.
- **`grid` + `plot` as a bar chart.** I used a grid with only an x axis (`major: 37.5`,
  `label_step: 500`) and a 5-row data y axis. Each series was `[[0, row], [value, row]]` with
  `stroke_width: 4.6, marker: "none"`, so the bar lengths came out in data values with no mm
  maths.
- **`defaults`** (`layer`, `font_family`) kept the 40-element card batch readable. Style dicts
  pass through unknown CSS (`{"letter-spacing": "0.9"}` worked for the kicker).
- The exports were right first time: `dpi: 300, background: "#ffffff"` → 3508 x 4961 px. The PDF
  embeds the fonts.

## What was awkward (agent had to compute, retry, or work around)
- **The timeline geometry was all hand arithmetic.** I computed node y = 78 + 29·i. From it I
  derived the card top (y − 12), year and title baselines (top + 11.5), description baseline
  (top + 19), pointer-triangle points (3 per card) and card x (16 vs 163, alternating). That gave
  8 × 5 elements with computed coordinates, plus 16 badge circles. `layout` cannot express
  "alternate sides of an axis" or "the same block of 5 elements repeated with an offset".
- **Card height was estimated from font metrics.** I worked out the year cap-height (≈ 0.7 × 8)
  and the last description baseline (19 + 2 × 3.5 × 1.35) plus descender to get 35 mm. That needed
  a second `update_elements` for all 8 rects. There is no "box that fits its text + padding".
- **The title's x offset after the year** (x + 29 / x + 23) was a guess at the width of "1903"
  in Georgia Bold 8 mm. It happened to look right, but `layout` per card would have taken 8 more
  calls.
- **Bar chart workarounds:**
  - There is no bar series, so the bars are thick polylines.
  - I wanted vertical gridlines only. A y `major` equal to the full height still draws the top
    and bottom horizontal lines.
  - The category names are hand-placed text with `text_anchor: end` at a computed x.
  - Labels that did not fit to the right of the long bars (they crossed the 1500 and 2500
    gridlines) had to go *inside* the bars: a computed x, `text_anchor: end` and a white fill.
- **`label_offset` semantics are undocumented.** I passed `[2, 1]`, assuming the label sat on the
  baseline. In fact it is already vertically centred on the point, so the labels came out 1 mm
  low and needed an `align` pass (`"moved": {"text83": [0.0, -1.0], ...}` for all 5).
- **`plot` returns generic ids** (`"line": "polyline82"`, `"labels": ["text83"]`) even though each
  series had an `id` (`bar_wright`). I had to copy the ids from the response to address them later.
- The grid tick labels are bold by default (bold_major). I left them bold, but on a light chart
  they are heavier than the data labels.

## Missing tools or options
- A **repeat/template** mechanism: a block of element specs with placeholders
  (`{year}`, `{title}`, `{desc}`), stamped for a list of rows with a step (`[0, 29]`) and optional
  mirroring about an axis (`x = 148.5`) on alternate rows. That covers timelines, card grids and
  legends.
- A **text box / card** element: a rect that sizes itself to its text (padding, rx, fill), or
  `fit_to` on a rect (`{"id": "card1", "fit_to": ["year1", "title1", "desc1"], "padding": [6, 6]}`).
- **Bars in `plot`** (`"type": "bar"`, `"orientation": "horizontal"`, `bar_width`), a category
  axis (`"y": {"categories": [...]}`) that labels rows, and value labels that go inside or outside
  automatically.
- **Grid: gridlines per axis on/off** (e.g. `y: {"lines": false}`) and `bold_major: false`
  documented in the tool description.
- **Print options on `export`**: bleed (extend background rects by 3 mm and export the area with
  bleed), crop marks, and a note on CMYK. The PDF is RGB, so "print-ready" was as far as the tools
  allow.
- `plot` label placement: document the default anchor (vertically centred, left-aligned?) and
  support `label_anchor: "start" | "end" | "inside_end"`.

## Bugs / surprising behaviour (with the exact call and response)
- **Plot value labels carry a hidden white halo stroke**, so changing their fill to white turned
  them into blobs:
  `update_elements({"updates": [{"id": "text89", "x": 164, "text_anchor": "end", "fill": "#ffffff", "font_weight": "bold"}, {"id": "text91", ...}]})`
  → `{"doc_id":"doc1","updated":2}`. The following `render_preview` showed "1,127 km/h (Mach 1.06)"
  as a white, unreadable smear on the navy bar. Fix: a second call with
  `{"id": "text89", "stroke": "none"}`. The halo is useful on the grid, but the `plot` tool
  description does not mention it. A `label_halo` option (as on `connect`) would
  make it discoverable.
- `label_offset: [2, 1]` → labels 1 mm below the bar centre (see above). Not a bug if intended,
  but it surprised me.
- No tool call returned an error.

## Suggestions
- **The single new tool that would have helped most: `repeat` (stamp a template of elements for
  N rows with a step and optional alternate mirroring).** The timeline was ~60 hand-positioned
  elements. With `repeat` plus the existing text wrapping it would have been one call with 8 rows
  of data, and card height could follow from `wrapped_lines`.
- Runner-up: a bar-series mode in `plot` with a category axis. Together with `grid` it would make
  the chart section 2 calls with no label fixes.
- Name `plot` outputs after the series id (`bar_wright_line`, `bar_wright_label_1`).
- Mention in the `plot` description that point labels have a white halo, and where they are
  anchored.
