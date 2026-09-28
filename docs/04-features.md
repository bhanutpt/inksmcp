# Features

Status legend: 💡 idea · 📋 planned · 🚧 in progress · ✅ done (tested) · ❌ dropped

"Agent load" = what the agent no longer has to compute or remember because the tool does it.

## MCP tools

| Tool | Purpose | Status | Agent load removed | Tests |
|---|---|---|---|---|
| `inkscape_info` | Inkscape version/path, open documents | ✅ | — | e06 |
| `document_create` | New doc; viewBox = size so coords are in `unit`; optional background | ✅ | unit/viewBox maths | `test_poster_workflow` |
| `document_open` | Open SVG, returns outline | ✅ | — | — |
| `document_save` | Save Inkscape SVG | ✅ | — | `test_poster_workflow` |
| `inspect` | Outline tree + **real visual bboxes in user units** (text too); big layers summarised, `layer` drill-down | ✅ | measuring text, px→unit conversion, context flooding (E14) | `test_poster_workflow`, `test_outline_summarises_*` |
| `add_elements` | Batch add rect/circle/ellipse/line/polyline/polygon/path/text/group; style shorthands; layers by name; multi-line text; `preview` | ✅ | many round-trips, style syntax, layer bookkeeping, invisible-line defaults | `test_poster_workflow`, `test_document.py` |
| `update_elements` | Batch partial update (geometry, style merge, transform, rename) | ✅ | — | `test_document.py` |
| `delete_elements` | Delete by id | ✅ | — | — |
| `path_operation` | union/difference/intersection/exclusion/division/cut/combine/break_apart/to_path/stroke_to_path/simplify/flatten; reports `result` (surviving/new ids; combine keeps the top id, F30) and removed/created ids | ✅ | selection handling, id tracking, working out the survivor (field report 7) | `test_union_keeps_style`, `test_path_operation_names_the_result` |
| `run_actions` | Guarded escape hatch for raw Inkscape actions | ✅ | — | `test_blocked_actions` |
| `export` | png/pdf/svg/plain-svg/eps/ps/emf/wmf; page/drawing/`region`/ids (several ids fixed, `only_ids`); dpi/size/background | ✅ | sticky-export traps, px areas | `test_export_*`, `test_field_report_1.py` |
| `render_preview` | PNG back to the agent; zoom with `region` or `ids` (everything visible), `only_ids` to isolate | ✅ | checking details (field report) | `test_render_png…`, `test_multi_id_export_and_preview` |
| `grid` | Graph paper / chart grids: linear or log per axis, 3 weight classes, border, measured edge labels; spacings must nest (lines classed by index); log `labels` decades (default with `start`) or paper (D-023) | ✅ | computing hundreds of scale positions, label offsets (field reports 1, 10) | `test_log_log_grid_a4`, `test_tools_from_field_report`, `test_linear_ticks_class_lines_by_index`, `test_log_labels_follow_start` |
| `repeat` | Stamp a template once per data row: `{key}` placeholders, local ids (`card` → `card-<n>`), step or grid `columns`, alternate `mirror` about an axis (shapes reflected, texts/groups moved as blocks), off-page warnings, all or nothing | ✅ | hand-computed positions for every repeated block (field report 3: ~60 elements) | `test_repeat.py` |
| rect `fit_to` | Rect sized around other elements' measured bboxes after wrapping: `fit_padding`, `fit` both/height/width; re-fits when targets are edited, chains (panel around cards) in dependency order, works in transformed groups and `repeat` templates | ✅ | card heights estimated from font metrics + a second update (field report 3) | `test_fit.py` |
| All-or-nothing tools | Any failure restores the document ("Nothing was changed."); a dead Inkscape shell is retried once per pass; `ShellDied` names the exit code and command (D-022) | ✅ | half-applied batches after a crash (field report 5) | `test_failed_tools_leave_the_document_unchanged`, `test_a_pass_is_retried_when_the_shell_dies` |
| `clip` key | Any element: an element id (shape copied) or `[x, y, w, h]`; clipped bbox measured; moves with the element; `null` removes (D-025, F32) | ✅ | `run_actions object-set-clip` recipe (field reports 5, 8) | `test_clip_to_a_panel_follows_the_element`, `test_repeat_clips_each_row_to_its_own_frame` |
| text `halo` | `halo` colour + `halo_width` (default 0.3 × font size), `'none'` removes (S11) | ✅ | paint-order styles by hand (field report 8) | `test_text_halo_key` |
| connector layers, label ids, gaps | Default layer: the ends' shared layer or "Connectors"; response lists `layers` and `labels`; `start_gap`/`end_gap` (inksmcp routing) | ✅ | loose connectors, hidden label ids, arrowheads touching text (field reports 6, 9) | `test_connect_layers_labels_and_end_gap` |
| `repeat` response & order | Id runs shortened (`card-1..card-12`); `order: "column"`; `id_prefix` clash rejected; description teaches the component pattern and reserved `n`/`i` | ✅ | 8k-char responses, 6+5 legend columns, clash (field reports 5, 6) | `test_compact_ids_and_column_order`, `test_repeat_rejects_id_prefix_equal_to_a_template_id` |
| `add_elements` `defaults` | One style/layer object merged into every spec (font keys only for text) | ✅ | repeated payload (field report) | `test_tools_from_field_report` |
| `plot` | Data series on a `grid` in data values: line, markers, point labels; out-of-range warnings | ✅ | data→coordinate maths (field report 2) | `test_plot_cop_chart` |
| `plot` ids & labels | Child ids follow the series id (`<id>-line`, `-marker-k`, `-label-k`); `label_halo` ("none" for dark fills), `label_anchor`; label centring documented | ✅ | copying generic ids, white-blob labels, 1 mm guess (field report 3) | `test_plot_ids_follow_series_id_and_label_options` |
| `grid` axis `lines: false` | Keep an axis for labels/`plot` but draw none of its gridlines (bar charts) | ✅ | top/bottom lines drawn by a fake y major (field report 3) | `test_grid_axis_without_lines` |
| `grid` titles | `x_title` / `y_title` placed from measured tick labels (y rotated) | ✅ | hand transforms | `test_plot_cop_chart` |
| connector sides/via | `from_side`/`to_side` (+elbow) and `via` waypoints, routed by inksmcp and kept attached | ✅ | helper objects, split connectors (field report 2) | `test_connect_with_sides…`, `test_route_elbow_textbook_cases` |
| connector labels | `label_position`, `label_side`, `label_offset`, `font_family`/`font_weight`, `label_halo` | ✅ | labels on corners / through text | `test_connect_with_sides…`, `test_tools_from_field_report_2` |
| `marker_start`/`marker_end` | Arrowheads on line/polyline/path (flat-front marker, S10) | ✅ | — | `test_arrowheads_…` |
| `arrow` element | Block arrow x1,y1 → x2,y2 with shaft/head sizes, updatable | ✅ | 7-point polygons by hand | `test_block_arrow_element` |
| text `width` | Wrap to a width with measured word widths; paragraphs kept; re-wraps on change | ✅ | manual line breaks and baselines | `test_wrap_to_width` |
| multi-line text | Even line spacing, `line_height` works, indents preserved (F26) | ✅ | one text element per line | `test_multiline_text_has_even_line_spacing` |
| `move_to_layer` position | top / bottom | ✅ | extra z_order call | `test_move_to_layer_bottom` |
| hanging indents / lists | Numbered list with wrapped, indented continuation lines | 💡 | from E18 | |
| text `vertical_anchor` | `y` = cap top / cap middle / last baseline instead of first baseline (measured) | ✅ | guessed label offsets (field report) | `test_vertical_anchor_middle_and_top` |
| `align` | Batch align to page / selection / another id; `as_group`; `margin`; text by cap box so labels share baselines | ✅ | position & baseline maths, px↔unit conversion (E06→E08) | `test_align.py` |
| `connect` | Batch native connectors: straight/elbow, arrow end/start/both/none, colour, dash, midpoint label with halo; stay attached through align/layout/update; delete cascades | ✅ | endpoint maths, markers, re-routing (E06→E10) | `test_layout_connect.py` |
| `layout` | Row/column/grid with gap; items = id or [ids] moved together; block at first item / `at` / aligned `to` page or element | ✅ | position maths (E06→E10) | `test_layout_connect.py` |
| off-page warnings | `align`/`layout` report elements beyond the page | ✅ | noticing clipping in previews (E10) | `test_off_page_warning` |
| `page_fit` | Page = drawing (or ids) + margin (1/2/4 values); content moves, origin stays 0,0; backgrounds resized; connectors follow | ✅ | page maths, clipping fixes (E10→E12) | `test_page.py` |
| `page_resize` | Exact page size (A4 …), anchor top-left/center, off-page warnings | ✅ | — | `test_page_tools` |
| coordinate tidy | Moves snapped to 0.001; moved elements rounded to 4 decimals (F14, F19) | ✅ | cleaner SVG | `test_tidy_numbers…` |
| `distribute` | Equal spacing between first and last item within a span | 💡 | | |
| `z_order` | front/back/above/below (exact) and forward/backward (overlap-based); cross-layer above/below keeps visual position | ✅ | stacking bookkeeping, transform maths | `test_z_order.py` |
| `move_to_layer` | Move ids into a layer (by name, created) or group, keeping position | ✅ | transform compensation | `test_z_order.py` |
| font check | Warn when a requested font family isn't installed (silent fallback, S5) | 💡 | debugging "why does it look wrong" | |
| shell pre-warm | Start Inkscape shell at server start to hide the ~1.1 s first-call delay | 💡 | — | |
| gradients / markers / patterns | defs management | 💡 | | |
| `import` | Place images / other SVGs | 💡 | | |
| snapshots / undo | Restore previous document states | 💡 | | |

## MCP resources

| Resource | Purpose | Status | Notes |
|---|---|---|---|
| `inkscape://document/{id}` | Current document SVG | 💡 | |
| `inkscape://actions` | List of available Inkscape actions | 💡 | from `action-list` |

## MCP prompts

| Prompt | Purpose | Status | Notes |
|---|---|---|---|
| TBD | | | |
