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
| MCP `align` (measure + translate + preview), warm | ~400 ms |
| First Inkscape-backed call after server start | +~1.1 s (shell startup) |
| `add_elements` with 325 elements (stdio) | ~60 ms |
| A4 PNG export at 300 dpi (2480×3508, 325 lines) | ~0.4 s |
| `inspect` payload, 325 lines: before / after summarising | 30,806 / 600 chars (E14) |
| `grid` A4 log-log 3×5 with 74 measured labels: before / after batching | 11.2 s / 1.2 s incl. shell start (E16) |

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
| F12 | `object-align:<h\|v> <last\|first\|page\|…>` **works headless**. It uses the visual bbox and edits attributes (`x`, `cx`) rather than adding transforms. Leaves float junk (`-1.7763568e-15`). "last" = last id in `select-by-id`. | E07 | — (not used, see D-007) |
| F13 | **`transform-translate:dx,dy` takes px (96 dpi), not user units.** `10` in a mm doc moves 2.6458 mm. Positive dy = down. Inkscape handles parent transforms, groups and text. | E07, E07b | `test_align_to_page_edges_with_margin_mm`, `test_align_inside_transformed_group` |
| F14 | Inkscape writes coordinates with ~8 significant digits → a translated rect lands at `20.000042` not `20` (~4e-5 mm noise). Fixed by snapping moves to 0.001 units and tidying moved elements to 4 decimals. | E08, E12 | `test_tidy_numbers_only_touches_given_elements` |
| F15 | **Native connectors re-route headless.** A path with `inkscape:connector-type` + `inkscape:connection-start/end="#id"` gets its `d` computed **on load** (even from a dummy `M 0,0`) and again after `transform-translate`. So every round-trip through Inkscape refreshes routes. | E09, E09b | `test_connectors_follow_layout` |
| F16 | Connector endpoints are clipped to the **real shape** (circle edge at r=39.99, diamond vertices), work through transformed groups, `polyline` = straight, `orthogonal` = elbow (can produce a very short last segment). | E09b, E10 | `test_connect_attaches_to_edges` |
| F17 | **Text endpoints route from the text's centre** (line overlaps the letters) → warn and suggest the shape behind. | E09b | `test_text_endpoint_warns` |
| F18 | `page-fit-to-selection` works headless: resizes width/height/viewBox (units kept, origin stays 0) and **moves content** — adds `translate()` to layers, shifts top-level elements. No margin argument; a full-page background rect is shifted, not resized; with nothing selected it does nothing. | E11 | — (not used, see D-010) |
| F19 | `query-all` has ~6 significant digits in px → derived sizes carry ~1e-4 noise (100 mm page measured as 99.9999). | E11 (test failure) | `test_page_fit_with_margin` |
| F20 | **Translating a connector together with its endpoints moves it twice**: Inkscape re-routes it for the moved endpoints *and* applies the translate. Connectors must only follow. Inside a translated layer the route (layer coords) stays unchanged — correct. | E11 (test failure) | `test_translating_a_connector_directly_is_ignored`, `test_page_fit_moves_*connectors_along` |
| F22 | Z-order actions: `selection-raise`/`lower` are **overlap-based** (skip siblings that don't overlap; no-op if nothing overlaps). `selection-stack-up`/`down` move exactly one sibling. `selection-top`/`bottom` stay within the parent and keep relative order. Raising several ids at once gives unpredictable orders. **No headless move-to-layer action.** | E13 | `test_forward_backward_are_overlap_based` |
| F23 | **`export-id` takes exactly one id.** `export-id:a,b` looks for an object literally named `a,b`, prints `Object with id="a,b" was not found ... Skipping.` and writes nothing — our stderr patterns missed "was not found". | E15, field report | `test_export_id_takes_one_id_and_unknown_ids_now_raise` |
| F24 | `export-area:x0:y0:x1:y1` is in **px (96 dpi) relative to the viewBox origin**, not user units; everything on the page stays visible. | E15 | `test_region_export_is_in_user_units` |
| F25 | Shell cost is per *command line*, not per action: 300 × (select, translate) as separate lines 5.2 s; `;`-joined into one 16.7k-char line 0.57 s; one multi-id selection + one translate 33 ms. Long lines are safe (≥16.7k chars tested). | E16b | covered by the whole suite (22.7 s → 14.5 s) |
| F21 | With a non-zero viewBox origin, `query-all` positions are relative to the viewBox origin (px); adding the origin back gives user coordinates. | E11 | `test_page_fit_normalises_nonzero_viewbox_origin` |

## SVG behaviour

| # | Finding | Source | Guarded by |
|---|---|---|---|
| S1 | **Boolean ops drop presentation attributes** (`fill="…"`) → result turns black. `style="fill:…"` survives. Always write styles into `style`. | E01, E03 | `test_union_keeps_style`, `test_add_writes_style_attribute…` |
| S2 | Union result keeps the **bottom** object's id and style; the others are removed. | E01, E03 | `test_union_keeps_style` |
| S3 | Visual text bbox depends on glyphs: "Client" is 4.62 mm tall, "inksmcp" 6.0 mm (descender). Centring text by bbox ≠ centring by font metrics. | E06 | `test_centre_labels_in_boxes_share_baseline` |
| S4 | Text metrics scale exactly with font size (default sans: cap "H" = 0.714 em, "x" = 0.536 em, descender 0.240 em). But they **differ per font** (Arial 0.716, Times New Roman 0.694, Segoe UI 0.740…) → measure, don't assume. | E07, E07b | same |
| S5 | **Unknown font families silently fall back** to the default sans (identical metrics to `sans-serif`). No warning on stderr. | E07b | — (backlog: warn) |
| S6 | Inkscape honours `dominant-baseline` (central/middle/hanging) when measuring, but other renderers/PDF may not → we compute explicit `y` instead. | E07 | — |
| S7 | Markers render in headless PNG and PDF export. `orient="auto-start-reverse"` works; `fill:context-stroke` works in Inkscape PNG+PDF (but not all browsers → we use one marker per colour). | E09 | `test_connect_attaches_to_edges` |
| S8 | `query-all` bboxes of a path **include its markers** (line 70..180 → bbox 62..188). | E09 | — |
| S9 | Attributes in a custom namespace (`xmlns:inksmcp="urn:inksmcp"`) survive Inkscape SVG round-trips and plain-svg export. | E09 | `test_connector_label_sits_on_midpoint` |

## inkex

`inkex` is **not** importable from Inkscape's bundled `python.exe` by default (it lives in
`share/inkscape/extensions`). Not needed so far: lxml + the shell cover everything (see D-005).
