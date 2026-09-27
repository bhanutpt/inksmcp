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
| `inspect` | Outline tree + **real visual bboxes in user units** (text too) | ✅ | measuring text, px→unit conversion | `test_poster_workflow`, `test_bboxes…` |
| `add_elements` | Batch add rect/circle/ellipse/line/polyline/polygon/path/text/group; style shorthands; layers by name; multi-line text; `preview` | ✅ | many round-trips, style syntax, layer bookkeeping, invisible-line defaults | `test_poster_workflow`, `test_document.py` |
| `update_elements` | Batch partial update (geometry, style merge, transform, rename) | ✅ | — | `test_document.py` |
| `delete_elements` | Delete by id | ✅ | — | — |
| `path_operation` | union/difference/intersection/exclusion/division/cut/combine/break_apart/to_path/stroke_to_path/simplify/flatten; reports removed/created ids | ✅ | selection handling, id tracking | `test_union_keeps_style` |
| `run_actions` | Guarded escape hatch for raw Inkscape actions | ✅ | — | `test_blocked_actions` |
| `export` | png/pdf/svg/plain-svg/eps/ps/emf/wmf; page/drawing/ids; dpi/size/background | ✅ | sticky-export traps | `test_export_*` |
| `render_preview` | PNG image back to the agent (longest side = `max_size`) | ✅ | — | `test_render_png…` |
| `align` | Batch align to page / selection / another id; `as_group`; `margin`; text by cap box so labels share baselines | ✅ | position & baseline maths, px↔unit conversion (E06→E08) | `test_align.py` |
| `connect` | Batch native connectors: straight/elbow, arrow end/start/both/none, colour, dash, midpoint label with halo; stay attached through align/layout/update; delete cascades | ✅ | endpoint maths, markers, re-routing (E06→E10) | `test_layout_connect.py` |
| `layout` | Row/column/grid with gap; items = id or [ids] moved together; block at first item / `at` / aligned `to` page or element | ✅ | position maths (E06→E10) | `test_layout_connect.py` |
| off-page warnings | `align`/`layout` report elements beyond the page | ✅ | noticing clipping in previews (E10) | `test_off_page_warning` |
| `page_fit` | Page = drawing (or ids) + margin (1/2/4 values); content moves, origin stays 0,0; backgrounds resized; connectors follow | ✅ | page maths, clipping fixes (E10→E12) | `test_page.py` |
| `page_resize` | Exact page size (A4 …), anchor top-left/center, off-page warnings | ✅ | — | `test_page_tools` |
| coordinate tidy | Moves snapped to 0.001; moved elements rounded to 4 decimals (F14, F19) | ✅ | cleaner SVG | `test_tidy_numbers…` |
| `distribute` | Equal spacing between first and last item within a span | 💡 | | |
| `z_order` | raise/lower/top/bottom | 💡 | | |
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
