# Tool reference

inksmcp exposes 24 tools. This page is generated from the server itself (`scripts/gen_tools_doc.py`), so it matches what an agent sees. For how the tools combine, see [recipes](recipes.md).

All coordinates are in the document's user units (the unit given at creation; origin top-left, y down). Tools act on the current document unless `doc_id` is given. Every tool is all-or-nothing: on an error nothing is changed.

- **Documents**: [`inkscape_info`](#inkscape_info), [`document_create`](#document_create), [`document_open`](#document_open), [`document_save`](#document_save), [`inspect`](#inspect)
- **Elements**: [`add_elements`](#add_elements), [`update_elements`](#update_elements), [`delete_elements`](#delete_elements), [`import_file`](#import_file), [`repeat`](#repeat)
- **Arrangement**: [`align`](#align), [`layout`](#layout), [`split`](#split), [`connect`](#connect), [`z_order`](#z_order), [`move_to_layer`](#move_to_layer), [`page_fit`](#page_fit), [`page_resize`](#page_resize)
- **Charts and paper**: [`grid`](#grid), [`plot`](#plot)
- **Paths and raw actions**: [`path_operation`](#path_operation), [`run_actions`](#run_actions)
- **Output**: [`render_preview`](#render_preview), [`export`](#export)

## Documents

### inkscape_info

Inkscape version and location, server version, and open documents.

No parameters.

### document_create

Create a new blank document and make it current. The viewBox matches width/height,
so coordinates are in `unit`. `background` (e.g. '#ffffff') adds a full-page rect with id 'background'.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `width` | number | required |  |
| `height` | number | required |  |
| `unit` | "px" \| "mm" \| "cm" \| "in" \| "pt" | "px" |  |
| `background` | string | null |  |

### document_open

Open an existing SVG (.svg or .svgz) and make it current. Returns its outline, and `notes` when the
file was normalised for editing without changing how it renders: a page whose viewBox doesn't match its
width/height (or uses %), fill/stroke set on the root (new elements would inherit them), ids given to
elements that had none.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | string | required |  |

### document_save

Save the document as Inkscape SVG (to `path`, or where it was opened/last saved).

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | string | null |  |
| `doc_id` | string | null |  |

### inspect

Outline of the document: layers, groups and elements with ids, fill/stroke as rendered (style,
attributes or inherited), text, `use` targets (href) and real visual bounding boxes [x, y, width, height]
in user units (measured by Inkscape). Layers/groups with more than `max_children` children are summarised
(counts per type, first/last ids, bbox). To list one of them, pass `layer` (layer name or group id) and a
larger max_children.
find: a flat list of matching elements instead of the tree, e.g. {"fill": "#99cc32"} (colours compared
in any notation), {"type": "text", "text": "total"}, {"type": "use", "href": "Parking"},
{"type": "symbol"} (symbols in defs, with titles), {"id_prefix": "card-"}.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `doc_id` | string | null |  |
| `bbox` | bool | true |  |
| `layer` | string | null |  |
| `max_children` | int | 40 |  |
| `find` | object | null |  |

## Elements

### add_elements

Add one or more elements in a single call. Returns the new ids.
Element spec keys — common: type, id, label, layer (name; created if missing), parent (group id), transform, style (css string or dict). Style shorthands: fill, stroke, stroke_width, opacity, fill_opacity, stroke_opacity, stroke_dasharray, stroke_linecap, stroke_linejoin, font_size, font_family, font_weight, font_style, text_anchor. Geometry per type: rect: x, y, width, height, rx, ry, fit_to, fit_padding, fit; circle: cx, cy, r; ellipse: cx, cy, rx, ry; line: x1, y1, x2, y2, marker_start, marker_end; polyline: points, marker_start, marker_end; polygon: points; path: d, marker_start, marker_end; text: x, y, text, line_height, vertical_anchor, width, halo, halo_width; group: -; arrow: x1, y1, x2, y2, shaft_width, head_width, head_length; image: x, y, width, height, href, object_fit, embed; use: x, y, width, height, href. points = [[x,y],...]. text supports '\n' for multiple lines; font_size is in user units. Coordinates are in the parent's system: inside a transformed layer or group (e.g. after layout moved it, or a scaled plan group) they are offset/scaled with it. use: href "symbol_id" places a symbol (or any element) of this document; "library.svg#symbol_id" copies that symbol from a file first (list a library's symbols: document_open it, inspect find {"type": "symbol"}); width/height scale a symbol that has a viewBox. clip: an element id (its current shape) or [x, y, w, h] — the element is cut to it and the clip then moves with the element; null removes it. text halo: '#ffffff' outlines the glyphs behind the fill so text reads over lines (halo_width default 0.3 x font size; 'none' removes). place: {"below": id, "gap": 1.5} (or above / left_of / right_of; "align": start|center|end on the other axis) puts the element beside the MEASURED box of another (real glyph extents, any script) and keeps it there when that element changes; inside repeat, ids are template names; null frees it. Responses warn about overlaps among the touched elements: text on text, text across a shape's edge, text crossed by a line (a text with a halo may cross lines). rect fit_to: [ids] sizes the rect around them after wrapping (fit_padding: n | [v, h] | [t, r, b, l]; fit: both | height | width, e.g. height keeps a card's width); it re-fits when those elements are edited (update_elements {"id": rect} re-fits after moves; fit_to: null frees it).
`defaults` is merged into every element (only keys valid for its type), e.g. {"font_size": 2.2, "fill": "#2a8a4a", "layer": "Labels"}.
elements_path: a JSON file (a list of specs, or {"elements": [...], "defaults": {...}}) instead of `elements` — for generated geometry, so it never passes through the conversation.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `elements` | list[object] | null |  |
| `defaults` | object | null |  |
| `elements_path` | string | null |  |
| `doc_id` | string | null |  |
| `preview` | bool | false |  |

### update_elements

Change existing elements. Each update is {"id": ..., <any element-spec keys>}; only the given
keys change. Style shorthands merge into the existing style. Set transform to "" to clear it.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `updates` | list[object] | required |  |
| `doc_id` | string | null |  |
| `preview` | bool | false |  |

### delete_elements

Delete elements (and their children) by id. Connectors attached to them and their labels
are deleted too; all removed ids are returned. Defs only they used (symbols of an imported library,
gradients, clip paths) go too: `defs_removed` counts them.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `ids` | list[string] | required |  |
| `doc_id` | string | null |  |

### import_file

Place a file into the current document. An SVG (e.g. geometry a script generated) becomes one
group scaled to this document's units, its top-left at `at` (default 0,0); width or height scales it
(both: stretch). Its layers become labelled groups, its defs join ours, clashing ids get "<id>-" in front.
An image (png/jpg/gif/webp/bmp) becomes an image element: natural size at 96 dpi unless width/height
(one keeps the ratio), linked by default (embed: true stores the pixels in the SVG), object_fit
contain|cover|fill for a given box. Relative paths start at the document's folder.
For whole documents use document_open; for data rows see repeat rows_path.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | string | required |  |
| `at` | list[number] | null |  |
| `width` | number | null |  |
| `height` | number | null |  |
| `layer` | string | null |  |
| `parent` | string | null |  |
| `id` | string | null |  |
| `embed` | bool | false |  |
| `object_fit` | "contain" \| "cover" \| "fill" | null |  |
| `doc_id` | string | null |  |
| `preview` | bool | false |  |

### repeat

Stamp a block of elements once per data row — timelines, card grids, tables, legends, map
symbols — in one call.
template: element specs as for add_elements, drawn for the FIRST row. "{key}" in any string is
replaced from the row ("{year}"; a value that is exactly "{w}" keeps the row's number), in geometry
and style alike ("fill": "{colour}"); "{n}" is the row number (1-based) and "{i}" the index, so
rows can't use the keys n and i. Ids are local names: "card" becomes card-1, card-2, ... A
"parent" may name another template element (e.g. a group holding a card and its texts); fit_to
and clip may name template elements of the same row.
Each row goes into a group <id_prefix>-<n> moved by n-1 steps: step [dx, dy], or a grid with
`columns` (step = [column pitch, row pitch]), filled row by row or, with order "column", column
by column. cell ["col", "row"]: each row is placed by its own 1-based column/row values (gaps and
fractions allowed: periodic tables, calendars, timetables, lanes); the template is drawn for cell
(1, 1) and step is the [column, row] pitch. Components (a character, a node, a symbol placed at data positions): a template group
with "transform": "translate({x},{y}) scale({s})" and step [0, 0], parts drawn around a local
origin, pose/shape parts as placeholders ("d": "{arms}").
mirror {"x": 148.5, "rows": "even"|"odd"|"all"} (or "y") mirrors those rows about the axis:
shapes are reflected (pointers flip), texts and groups keep their reading direction and move as
blocks — group a card with its texts so they cross together. Per element "mirror":
"reflect"|"block"|"none" overrides. rows_path: a .json (list of row objects) or .csv file (header
line = keys, numbers parsed) instead of `rows`, so data never passes through the conversation.
Returns the row groups, ids per template name (runs shortened to "card-1..card-12"), wrapped_lines, fitted.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `template` | list[object] | required |  |
| `step` | list[number] | required |  |
| `rows` | list[object] | null |  |
| `rows_path` | string | null |  |
| `columns` | int | null |  |
| `mirror` | object | null |  |
| `defaults` | object | null |  |
| `id_prefix` | string | "row" |  |
| `layer` | string | null |  |
| `order` | "row" \| "column" | "row" |  |
| `cell` | list[string] | null |  |
| `doc_id` | string | null |  |
| `preview` | bool | false |  |

## Arrangement

### align

Align elements to the page, to each other, or inside another element — e.g. centre a label in a box:
{"ids": ["label"], "to": "box", "horizontal": "center", "vertical": "middle"}. Operations run in order,
each seeing the previous moves. Returns the moves [dx, dy] and new bboxes in user units.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `operations` | list[AlignOp] | required |  |
| `doc_id` | string | null |  |
| `preview` | bool | false |  |

`AlignOp` fields:

| Field | Type | Default | Description |
|---|---|---|---|
| `ids` | list[string] | required | Elements to move. |
| `to` | string | "page" | Reference: 'page', 'selection' (bbox of all ids), or an element id. |
| `horizontal` | "left" \| "center" \| "right" | null |  |
| `vertical` | "top" \| "middle" \| "bottom" | null |  |
| `as_group` | bool | false | Move all ids together, keeping their relative positions. |
| `margin` | number | 0 | Inset from the reference edge in user units (ignored for center/middle). |
| `text_metrics` | "cap" \| "visual" | "cap" | For text: 'cap' aligns vertically by cap-height..baseline so one-line Latin labels share baselines (default); 'visual' uses the glyph bbox — better for paragraphs and scripts without Latin capitals (Tamil, Devanagari, CJK). |

### layout

Arrange items in a row, column or grid with a gap — no coordinate maths needed.
An item is an id or a list of ids that move together, e.g. ["box1", "box1_label"], or
{"ids": [...], "anchor": "fig1-border"} to arrange by that member's box (plot frames line up even when
their tick labels differ in width); the rest moves along.
`gap` is a number or [horizontal, vertical]. `align` places items on the cross axis (grid: within cells).
The block stays where the first item is, or its top-left goes to `at` [x, y], or it is aligned to
`to` ('page' or an element id) using horizontal/vertical/margin. Connectors follow.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `items` | list[string \| list[string] \| object] | required |  |
| `direction` | "row" \| "column" \| "grid" | "row" |  |
| `gap` | number \| list[number] | 0 |  |
| `columns` | int | null |  |
| `align` | "start" \| "center" \| "end" | "center" |  |
| `at` | list[number] | null |  |
| `to` | string | null |  |
| `horizontal` | "left" \| "center" \| "right" | null |  |
| `vertical` | "top" \| "middle" \| "bottom" | null |  |
| `margin` | number | 0 |  |
| `doc_id` | string | null |  |
| `preview` | bool | false |  |

### split

Divide a region into named cells — comic panels, dashboard tiles, poster columns, table grids —
without computing any positions. region: "page", an element id (its measured box) or [x, y, w, h];
margin insets it (one number, [vertical, horizontal] or [top, right, bottom, left]).
rows: one entry per row, either a number of equal columns or a list of column ratios, e.g.
[[2, 1], [1, 1], [1, 2]]; heights: row ratios (default equal); gutter: space between cells
(number or [horizontal, vertical]).
Creates one rect per cell, <id_prefix>-1, -2, ... row by row, in `layer` — invisible unless `style`
gives e.g. {"fill": "#fff", "stroke": "#000", "stroke_width": 0.6, "rx": 2}. Use the ids as targets:
clip ("clip": "cell-5"), align/layout ("to": "cell-2"), place, fit, connect. An element region is its
measured box (stroke included).
Tables: split the header strip into columns (e.g. rows [[3, 1, 1]]), then `repeat` the data rows with
step [0, row pitch] and texts at the returned column edges (numbers: text_anchor end at the right edge).
Returns the cells [x, y, w, h] and their ids per row.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `rows` | list[int \| list[number]] | required |  |
| `region` | string \| list[number] | "page" |  |
| `heights` | list[number] | null |  |
| `gutter` | number \| list[number] | 0 |  |
| `margin` | number \| list[number] | 0 |  |
| `id_prefix` | string | "cell" |  |
| `layer` | string | "Cells" |  |
| `style` | object | null |  |
| `doc_id` | string | null |  |
| `preview` | bool | false |  |

### connect

Draw arrows/lines between elements that stay attached when things move (align/layout/
update_elements/page_fit). Default: native Inkscape connectors — clipped to the real shape (circles
etc.) and still live in the Inkscape GUI. With from_side/to_side/via you control the route (e.g. a
loop diagram: {"from": "condenser", "to": "valve", "from_side": "left", "to_side": "top",
"routing": "elbow"}); those attach at the middle of the chosen side of the bounding box, as do
connectors with start_gap/end_gap. Returns the connector ids, their layers, label ids and warnings.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `connections` | list[Connection] | required |  |
| `doc_id` | string | null |  |
| `preview` | bool | false |  |

`Connection` fields:

| Field | Type | Default | Description |
|---|---|---|---|
| `from` | string | required | Start element id (a shape; text routes from its centre). |
| `to` | string | required | End element id. |
| `id` | string | null |  |
| `routing` | "straight" \| "elbow" | "straight" | elbow = orthogonal segments. |
| `arrow` | "end" \| "start" \| "both" \| "none" | "end" |  |
| `stroke` | string | "#000000" |  |
| `stroke_width` | number | null | Default ≈1.5 px in user units. |
| `stroke_dasharray` | string | null | e.g. '4 2' for dashed. |
| `from_side` | "top" \| "right" \| "bottom" \| "left" \| "auto" | null | Leave `from` through this side (then the route is computed by inksmcp, not Inkscape). |
| `to_side` | "top" \| "right" \| "bottom" \| "left" \| "auto" | null | Enter `to` through this side. |
| `via` | list[list[number]] | null | Waypoints [[x, y], ...] the line passes through (corners of a loop, detours). |
| `label` | string | null | Text placed on the route (default: middle of the longest segment). |
| `label_position` | number | null | 0..1 along the route instead of the longest segment. |
| `label_offset` | number | null | Distance of the label from the line (user units). 0 = on the line with a halo. |
| `label_side` | "auto" \| "above" \| "below" \| "left" \| "right" | null | Where an offset label goes; auto = above horizontal segments, right of vertical ones. |
| `label_halo` | string | null | Halo colour behind an on-line label, or 'none' (default white). |
| `label_color` | string | null |  |
| `font_size` | number | null |  |
| `font_family` | string | null |  |
| `font_weight` | string | null |  |
| `start_gap` | number | null | Leave this much space before the line starts (user units). |
| `end_gap` | number | null | Stop this far short of `to` (e.g. so an arrowhead doesn't touch text). |
| `layer` | string | null | Default: the layer both ends are in, else a 'Connectors' layer. |

### z_order

Change stacking order (what is drawn on top). front/back: top/bottom within the element's own
layer or group. forward/backward: one step past the next object it overlaps (visible change).
above/below: directly above/below `target`, moving into target's layer/group if needed while keeping
the visual position. Several ids keep their relative order. Returns each id's position.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `ids` | list[string] | required |  |
| `operation` | "front" \| "back" \| "forward" \| "backward" \| "above" \| "below" | required |  |
| `target` | string | null |  |
| `doc_id` | string | null |  |
| `preview` | bool | false |  |

### move_to_layer

Move elements into a layer (by name; created on top if missing) or into a group/layer by id,
at its top or bottom. They keep their relative order and stay visually where they were.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `ids` | list[string] | required |  |
| `layer` | string | required |  |
| `position` | "top" \| "bottom" | "top" |  |
| `doc_id` | string | null |  |
| `preview` | bool | false |  |

### page_fit

Resize the page to fit the drawing (or only `ids`) plus `margin` (one number, [vertical, horizontal]
or [top, right, bottom, left], user units). All content moves together so the page keeps its 0,0
top-left; full-page background rects are resized, connectors follow.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `margin` | number \| list[number] | 0 |  |
| `ids` | list[string] | null |  |
| `doc_id` | string | null |  |
| `preview` | bool | false |  |

### page_resize

Set the page size in user units (e.g. 210 x 297 for A4 in a mm document). anchor='center' keeps the
drawing centred on the new page; 'top-left'/'none' leave content where it is. Backgrounds are resized.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `width` | number | required |  |
| `height` | number | required |  |
| `anchor` | "top-left" \| "center" \| "none" | "top-left" |  |
| `doc_id` | string | null |  |
| `preview` | bool | false |  |

## Charts and paper

### grid

Draw a grid / graph paper inside rect [x, y, w, h] — linear or logarithmic per axis — without
computing any line positions. Axis specs:
  linear: {"scale": "linear", "major": 10, "medium": 5, "minor": 1, "label_start": 0, "label_step": 1}
          (spacings in user units, each a whole multiple of the finest; labels on major lines)
  log:    {"scale": "log", "cycles": 3, "subdivisions": "standard" | "fine" | "integers", "start": 10}
          (decades major, 2..9 medium, subdivisions minor; "start" = value at the origin (default 1);
          "labels": "decades" (start, start*10, ...; default when start is given) | "paper" (1..9 per cycle))
  "reverse": true flips an axis (default x left→right, y bottom→top); "lines": false keeps the axis
  (labels, `plot` mapping) but draws none of its gridlines, e.g. vertical-only lines for a bar chart.
weights: {"major", "medium", "minor"} stroke widths (defaults 0.45/0.22/0.08 mm); border: stroke width
of the frame (default 0.6 mm, 0 = none). labels: {"sides": ["left", "bottom"], "font_size", "gap",
"color", "font_family", "bold_major", "x_title", "y_title", "title_font_size"} — placed outside the
grid, centred on their lines (measured); major labels are bold unless "bold_major": false; titles go
below / left (rotated) of the tick labels.
Result: one path per weight class in layers '<layer_prefix> minor/medium/major', labels in
'<layer_prefix> labels'. Use `plot` with grid=<id_prefix> to draw data on it.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `rect` | list[number] | required |  |
| `x` | object | null |  |
| `y` | object | null |  |
| `color` | string | "#7f7f7f" |  |
| `weights` | object | null |  |
| `border` | number | null |  |
| `labels` | object | null |  |
| `layer_prefix` | string | "Grid" |  |
| `id_prefix` | string | "grid" |  |
| `doc_id` | string | null |  |
| `preview` | bool | false |  |

### plot

Plot data on a grid made with the `grid` tool, in DATA values — no coordinate maths.
grid: that grid's id_prefix. Each series: {"points": [[x, y], ...], "line": true, "stroke": "#1f77b4",
"stroke_width", "stroke_dasharray", "marker": "circle"|"square"|"diamond"|"none", "marker_size",
"marker_fill" (default white), "point_labels": ["", "COP 3.2", ...] (one per point, null/"" to skip),
"label_offset": [dx, dy], "label_anchor": "start"|"middle"|"end", "label_halo": "#ffffff"|"none",
"label_font_size", "label_color", "font_family", "id", "layer"}.
Labels: label_offset is from the point to the label's anchor, and the label is vertically CENTRED on
point + dy (dy = 0 → centred on the point). Anchor defaults to start for dx >= 0, else end. Without
label_offset the label goes right of the point, on the side the line is not heading to. Labels carry a
halo stroke (default white) so the line can cross them — set label_halo "none" (or the background
colour) for labels on dark fills; recolouring a label later does not remove its halo (use stroke: "none").
Ids follow the series id: <id>-line, <id>-marker-<k>, <id>-label-<k> (k = 1-based point index).
Returns per series those ids and the points in user units (for annotations); warns about points
outside the grid.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `series` | list[object] | required |  |
| `grid` | string | "grid" |  |
| `doc_id` | string | null |  |
| `preview` | bool | false |  |

## Paths and raw actions

### path_operation

Geometry operations performed by Inkscape on the given ids. For difference, the top-most
(later in document order) object is subtracted from the bottom one. to_path converts shapes
and text into paths. union/intersection/exclusion/difference keep the BOTTOM object's id, style
and layer; combine keeps the TOP object's (E22). `result` lists the ids that hold the outcome.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `operation` | "union" \| "difference" \| "intersection" \| "exclusion" \| "division" \| "cut" \| "combine" \| "break_apart" \| "to_path" \| "stroke_to_path" \| "simplify" \| "flatten" | required |  |
| `ids` | list[string] | required |  |
| `doc_id` | string | null |  |
| `preview` | bool | false |  |

### run_actions

Escape hatch: run raw Inkscape actions (e.g. "object-align:left last", "transform-rotate:30")
after selecting `select` ids. File, export, window and quit actions are blocked.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `actions` | list[string] | required |  |
| `select` | list[string] | null |  |
| `doc_id` | string | null |  |
| `preview` | bool | false |  |

## Output

### render_preview

Render to a PNG image you can look at (white background, longest side = max_size px).
Zoom in with `region` [x, y, w, h] in user units, or with `ids` (the area around them, everything
still visible). only_ids=true draws just those objects.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `max_size` | int | 800 |  |
| `area` | "page" \| "drawing" | "page" |  |
| `ids` | list[string] | null |  |
| `region` | list[number] | null |  |
| `only_ids` | bool | false |  |
| `doc_id` | string | null |  |

### export

Export via Inkscape. Format defaults to the file extension. What is exported:
`region` [x, y, w, h] (user units, everything visible); or `ids` — only those objects cropped to
them (only_ids=true, default) or the area around them with everything visible (only_ids=false);
otherwise area 'page' or 'drawing'. For PNG set dpi or width/height (px); background e.g. '#ffffff'
(default transparent).

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | string | required |  |
| `format` | "png" \| "pdf" \| "svg" \| "plain-svg" \| "eps" \| "ps" \| "emf" \| "wmf" | null |  |
| `area` | "page" \| "drawing" | "page" |  |
| `ids` | list[string] | null |  |
| `only_ids` | bool | true |  |
| `region` | list[number] | null |  |
| `dpi` | number | null |  |
| `width` | int | null |  |
| `height` | int | null |  |
| `background` | string | null |  |
| `text_to_path` | bool | false |  |
| `doc_id` | string | null |  |
