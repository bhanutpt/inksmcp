# Recipes

How the tools combine for common jobs. Each block is one tool call: `// tool_name` followed by its JSON
arguments, as an agent would send them. **Every recipe on this page is run by the test suite**
(`tests/test_recipes.py`), so the calls are known to work.

You rarely need to write these yourself: describe what you want to your assistant, and it picks the
tools. The recipes show what it can do, and they help when you're writing prompts, reviewing a session,
or building on inksmcp.

- [A poster in four calls](#a-poster-in-four-calls)
- [Cards from data: repeat, fit_to and place](#cards-from-data)
- [Panels and tables: split](#panels-and-tables)
- [A flowchart that stays connected](#a-flowchart-that-stays-connected)
- [Charts on real axes: grid and plot](#charts-on-real-axes)
- [Big data without big prompts: files in](#big-data-without-big-prompts)
- [Editing a file someone else made](#editing-a-file-someone-else-made)
- [Checking and exporting](#checking-and-exporting)

## A poster in four calls

Create a page, add everything in one batch, centre it, export. Coordinates are in the document's unit
(mm here); `layer` names create layers on the fly.

```json
// document_create
{"width": 210, "height": 297, "unit": "mm", "background": "#fdf8ef"}
```

```json
// add_elements
{"elements": [
  {"type": "text", "id": "title", "x": 0, "y": 40, "text": "Night Sky Walk", "font_size": 16,
   "font_weight": "bold", "fill": "#1d2b4f", "layer": "Text"},
  {"type": "text", "id": "sub", "x": 0, "y": 0, "text": "Saturday 21:00, meet at the old gate", "font_size": 6,
   "fill": "#1d2b4f", "layer": "Text", "place": {"below": "title", "gap": 4, "align": "center"}},
  {"type": "circle", "id": "moon", "cx": 105, "cy": 150, "r": 40, "fill": "#f4d35e", "layer": "Art"}
]}
```

```json
// align
{"operations": [{"ids": ["title", "sub"], "to": "page", "horizontal": "center", "as_group": true}]}
```

```json
// export
{"path": "night-sky-walk.pdf"}
```

`place` keeps the subtitle below the title's *measured* glyphs, so it follows when the title changes.

## Cards from data

`repeat` stamps a template once per data row. `{key}` placeholders are filled from each row, ids become
`card-1`, `card-2`, and so on, and `fit_to` sizes each card's box around its own texts after wrapping.
Here the cards form a timeline.

```json
// document_create
{"width": 297, "height": 120, "unit": "mm"}
```

```json
// repeat
{"rows": [
  {"year": 1903, "text": "First powered flight at Kitty Hawk."},
  {"year": 1927, "text": "First solo nonstop flight across the Atlantic, New York to Paris."},
  {"year": 1969, "text": "Apollo 11 lands on the Moon."}],
 "step": [90, 0], "id_prefix": "entry",
 "template": [
  {"type": "group", "id": "card"},
  {"type": "rect", "id": "box", "parent": "card", "fit_to": ["year", "body"], "fit_padding": 4,
   "fill": "#ffffff", "stroke": "#264653", "stroke_width": 0.4, "rx": 2},
  {"type": "text", "id": "year", "parent": "card", "x": 15, "y": 30, "text": "{year}", "font_size": 9,
   "font_weight": "bold", "fill": "#e76f51"},
  {"type": "text", "id": "body", "parent": "card", "x": 15, "y": 0, "text": "{text}", "font_size": 4,
   "width": 60, "place": {"below": "year", "gap": 2}}
 ]}
```

The same pattern builds legends, badges, product cards and character poses. For a component placed at
data positions, give the template group `"transform": "translate({x},{y}) scale({s})"` and step `[0, 0]`.

## Panels and tables

`split` divides a region into named cells: comic panels, dashboard tiles, poster columns. Other tools
then target the cells by id: `clip` to a panel, `align` into it, `fit_to` around it.

```json
// document_create
{"width": 210, "height": 297, "unit": "mm"}
```

```json
// split
{"region": "page", "margin": 12, "gutter": 5, "rows": [1, [2, 1], 3], "heights": [2, 3, 2],
 "id_prefix": "panel", "style": {"fill": "#ffffff", "stroke": "#111111", "stroke_width": 0.8}}
```

```json
// add_elements
{"elements": [{"type": "circle", "id": "sun", "cx": 20, "cy": 20, "r": 30, "fill": "#f4a261",
               "clip": "panel-1"}]}
```

The sun is cut to the first panel and keeps its clip when it moves. For a **table**, split the header
strip into columns, then `repeat` the data rows with `step [0, row pitch]` and texts at the column
edges `split` returned.

## A flowchart that stays connected

Shapes and labels, labels centred in their shapes by cap height (so they share baselines), the pairs
laid out in a column, then connectors that stay attached when anything moves.

```json
// document_create
{"width": 120, "height": 160, "unit": "mm"}
```

```json
// add_elements
{"defaults": {"font_size": 4, "text_anchor": "middle"},
 "elements": [
  {"type": "rect", "id": "s1", "x": 0, "y": 0, "width": 50, "height": 14, "rx": 3, "fill": "#e8f1fb", "stroke": "#2b5797"},
  {"type": "text", "id": "t1", "x": 0, "y": 0, "text": "Order received"},
  {"type": "rect", "id": "s2", "x": 0, "y": 0, "width": 50, "height": 14, "rx": 3, "fill": "#e8f1fb", "stroke": "#2b5797"},
  {"type": "text", "id": "t2", "x": 0, "y": 0, "text": "Check stock"},
  {"type": "rect", "id": "s3", "x": 0, "y": 0, "width": 50, "height": 14, "rx": 3, "fill": "#e8f1fb", "stroke": "#2b5797"},
  {"type": "text", "id": "t3", "x": 0, "y": 0, "text": "Ship"}
 ]}
```

```json
// align
{"operations": [{"ids": ["t1"], "to": "s1", "horizontal": "center", "vertical": "middle"},
                {"ids": ["t2"], "to": "s2", "horizontal": "center", "vertical": "middle"},
                {"ids": ["t3"], "to": "s3", "horizontal": "center", "vertical": "middle"}]}
```

```json
// layout
{"items": [["s1", "t1"], ["s2", "t2"], ["s3", "t3"]], "direction": "column", "gap": 14, "at": [35, 20]}
```

```json
// connect
{"connections": [{"from": "s1", "to": "s2"}, {"from": "s2", "to": "s3", "label": "in stock"}]}
```

Centre the labels *before* `layout`: a label still sitting at 0,0 makes its pair measure too wide.
For loops and side exits use `from_side` / `to_side` / `via` on a connection.

## Charts on real axes

`grid` draws graph paper or chart axes (linear or log per axis) with measured labels; `plot` maps data
values onto it, so no coordinate maths is needed.

```json
// document_create
{"width": 160, "height": 110, "unit": "mm"}
```

```json
// grid
{"rect": [25, 10, 120, 80], "id_prefix": "cop",
 "x": {"scale": "linear", "major": 40, "minor": 8, "label_start": -10, "label_step": 10},
 "y": {"scale": "linear", "major": 16, "minor": 4, "label_start": 1, "label_step": 1},
 "labels": {"sides": ["left", "bottom"], "x_title": "Outdoor temperature (°C)", "y_title": "COP"}}
```

Linear spacings are in user units, and labels count from `label_start` in steps of `label_step`: here
one major square is 10 °C across and 1 COP up.

```json
// plot
{"grid": "cop", "series": [{"id": "cop35", "points": [[-10, 2.1], [0, 2.9], [10, 3.8], [20, 4.9]],
                            "stroke": "#e76f51", "marker": "circle"}]}
```

## Big data without big prompts

Generated geometry and long data tables shouldn't pass through the conversation. A script writes a
file; the tools read it.

- `add_elements` with `elements_path`: a JSON list of element specs.
- `repeat` with `rows_path`: a JSON list of rows or a CSV file with a header line.
- `import_file`: an SVG becomes one scaled group (its layers become groups, its ids made unique); an
  image becomes an `image` element (linked, or `embed: true`).

Relative paths start at the document's folder.

## Editing a file someone else made

`document_open` accepts `.svg` and `.svgz`. If the file's page is unusual (a `%` width, a viewBox that
doesn't match the page) or its root sets fill/stroke for everything, the file is normalised for editing
without changing how it looks, and the response's `notes` say what was done.

Find what to change by colour, type, text or symbol instead of by eye:

```json
// document_create
{"width": 100, "height": 60, "unit": "mm"}
```

```json
// add_elements
{"elements": [{"type": "circle", "id": "eye-l", "cx": 30, "cy": 30, "r": 6, "fill": "rgb(153,204,50)"},
              {"type": "circle", "id": "eye-r", "cx": 70, "cy": 30, "r": 6, "fill": "#99cc32"}]}
```

```json
// inspect
{"find": {"fill": "#99cc32"}}
```

```json
// update_elements
{"updates": [{"id": "eye-l", "fill": "#2a6fdb"}, {"id": "eye-r", "fill": "#2a6fdb"}]}
```

Export just the part you changed, as a 600 px wide PNG:

```json
// export
{"path": "eyes.png", "width": 600, "region": [20, 18, 60, 24]}
```

Colours match in any notation. `{"type": "symbol"}` lists a library's symbols with their titles, and
a `use` element places one straight from a library file: `{"type": "use", "href": "icons.svg#Parking",
"x": 10, "y": 10, "width": 12, "height": 12}`. Deleting elements also removes the defs only they used.

## Checking and exporting

- `render_preview` returns a PNG to the agent. Zoom with `region` or `ids`, and isolate elements with
  `only_ids`. Editing tools take `preview: true` to return one in the same call.
- Editing responses warn about overlaps they introduce: text on text, text across a shape's edge, text
  crossed by a line. Anything hidden under an opaque box is ignored.
- `export` writes PNG (`dpi` or `width`), PDF (`text_to_path` for print shops), plain SVG, EPS, PS, EMF
  or WMF, of the page, the drawing, some `ids` or a `region`.
