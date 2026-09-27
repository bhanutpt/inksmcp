# Features

Status legend: 💡 idea · 📋 planned · 🚧 in progress · ✅ done · ❌ dropped

## MCP tools

| Tool | Purpose | Status | Phase | Notes |
|---|---|---|---|---|
| `inkscape_info` | Report Inkscape version / path / health | 📋 | 1 | |
| `document_create` | New blank document (size, units) | 📋 | 1 | |
| `document_open` | Open an existing SVG | 📋 | 1 | |
| `document_save` | Save / save-as | 📋 | 1 | |
| `document_inspect` | Structured summary of layers & objects | 📋 | 1 | |
| `export` | Export to PNG / PDF / SVG | 📋 | 1 | |
| `render_preview` | Return a PNG preview to the AI | 📋 | 1 | |
| `shape_add` | Add rect / ellipse / line / path / polygon | 📋 | 2 | |
| `text_add` | Add / edit text | 📋 | 2 | |
| `style_set` | Fill, stroke, opacity, font | 📋 | 2 | |
| `layer_*` | Create / rename / reorder / hide layers | 📋 | 2 | |
| `transform` | Move / scale / rotate / align | 📋 | 2 | |
| `path_boolean` | Union / difference / intersection | 💡 | 3 | via Inkscape actions |
| `run_actions` | Escape hatch: raw Inkscape actions | 💡 | 3 | guarded |

## MCP resources

| Resource | Purpose | Status | Notes |
|---|---|---|---|
| `inkscape://document/{id}` | Current document SVG | 💡 | |
| `inkscape://actions` | List of available Inkscape actions | 💡 | from `--action-list` |

## MCP prompts

| Prompt | Purpose | Status | Notes |
|---|---|---|---|
| TBD | | | |
