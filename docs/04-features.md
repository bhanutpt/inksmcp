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
| `align` | Align/centre ids relative to page, selection or another id (incl. text in a box) | 📋 | baseline maths (E06) | |
| `connect` | Arrow/connector between two ids, auto edge points, arrowheads | 📋 | endpoint maths, markers (E06) | |
| `layout` | Row/column/grid distribution with gap | 📋 | position maths (E06) | |
| `z_order` | raise/lower/top/bottom | 💡 | | |
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
