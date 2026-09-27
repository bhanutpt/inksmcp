# Inkscape notes

Facts about Inkscape learned by **experiment** (scripts in [`experiments/`](../experiments/)).
Each finding names the experiment that proved it and, where it matters, the test that guards it.

## This machine (verified 2026-09-27)

| Item | Value |
|---|---|
| OS | Windows 11 Home |
| Inkscape | 1.4.4 (dcaf3e7, 2026-05-05) |
| Binary | `C:\Program Files\Inkscape\bin\inkscape.com` (on PATH) |
| Python | 3.12 via uv (`.python-version`); note: system `pip` belongs to 3.13 |
| MCP SDK | `mcp` 2.2.0 |

> On Windows use `inkscape.com` (console build, returns stdout/stderr); `inkscape.exe` is the GUI build.

## Performance (E01, E02, E05, E06)

| Operation | Time |
|---|---|
| Spawn `inkscape --version` (cold / warm) | ~3.8 s / ~0.6 s |
| Any one-shot CLI call (export, query, actions) | ~1.0–1.2 s |
| `--shell` startup | ~1.1 s (once) |
| One shell command | ~5–50 ms |
| open + query-all + close in shell | ~55 ms |
| MCP `inspect` / `export` over stdio (warm) | ~60–120 ms |

**→ Always use one persistent `--shell` process.** ~20× faster than spawning per call.

## CLI / shell behaviour

| # | Finding | Source | Guarded by |
|---|---|---|---|
| F1 | **Exit code is 0 even when actions fail.** Errors only appear on stderr (`could not find action`, `Did not find object with id`, `does not exist`, `no document!`, `Select <b>at least 1 path</b>…`). stderr contains GTK markup like `<b>`. | E01, E02, E04 | `test_unknown_action_raises…`, `test_missing_file_raises` |
| F2 | Shell protocol: banner, then prompt `"> "`. Every command is **echoed** back before its output. Long lines produce line-editing junk (`\r`, `\x08`) in the echo — strip the whole first line. | E02 | `test_long_command_echo_is_stripped` |
| F3 | stdout and stderr are separate pipes; stderr for a command may arrive just after the prompt → short grace period when reading. | E02 | — |
| F4 | `--query-all` returns `id,x,y,w,h` in **px at 96 dpi**, not user units. Divide by `width_px / viewBox_width`. Bounding boxes are *visual* (rotation, text glyphs included). | E04 | `test_bboxes_are_in_user_units_not_px` |
| F5 | **Export options are sticky for the whole shell session**, even across `file-close`/`file-open`: `export-id`, `export-width`, `export-type`, area mode… | E05, E05b | `test_export_settings_do_not_leak_between_exports` |
| F6 | Reset recipe: `export-id:;export-id-only:false;export-width:0;export-height:0;export-dpi:96` + exactly one area mode. `export-id:` alone is not enough. | E05c | same |
| F7 | `export-area-page` **beats** `export-id` (you get the page, not the object). With ids use `export-id:…;export-id-only:true;export-area-drawing`. | E06 (test failure) | same |
| F8 | Inkscape SVG export (`export-type:svg`, not plain) keeps layers (`inkscape:groupmode="layer"`) and ids. | E04 | `test_layers_survive_actions` |
| F9 | Action separators are `;` — paths containing `;` would break a command. Export to a temp file, then move. | design | `test_export_to_path_with_semicolon` |
| F10 | Bool export actions accept `:true` / `:false` arguments. | E05c | — |
| F11 | ~1073 actions (`--action-list`). Useful ones for later: `object-align`, `object-distribute`, `transform-*`, `selection-top/bottom/raise/lower`, `path-*`, `object-flip-*`. | E01 | — |

## SVG behaviour

| # | Finding | Source | Guarded by |
|---|---|---|---|
| S1 | **Boolean ops drop presentation attributes** (`fill="…"`) → result turns black. `style="fill:…"` survives. Always write styles into `style`. | E01, E03 | `test_union_keeps_style`, `test_add_writes_style_attribute…` |
| S2 | Union result keeps the **bottom** object's id and style; the others are removed. | E01, E03 | `test_union_keeps_style` |
| S3 | Visual text bbox depends on glyphs: "Client" is 4.62 mm tall, "inksmcp" 6.0 mm (descender). Centring text by bbox ≠ centring by font metrics. | E06 | — |

## inkex

`inkex` is **not** importable from Inkscape's bundled `python.exe` by default (it lives in
`share/inkscape/extensions`). Not needed so far: lxml + the shell cover everything (see D-005).
