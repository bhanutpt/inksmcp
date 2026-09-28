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
| F26 | **`sodipodi:role="line"` tspans with `dy` double the first line gap** in Inkscape (glyph bottoms 22.4 → 47.4 → 59.9 instead of 22.4 → 34.9 → 47.4); `line-height` style is then ignored. Correct: role=line + `line-height` in the text style + explicit `y` per tspan (also right in browsers, which ignore sodipodi:role). | E17, field report 2 | `test_multiline_text_has_even_line_spacing` |
| F27 | Inkscape 1.4 ignores `inkscape:connection-start-point` / `-end-point`: connectors still attach centre-to-edge. Side/port control has to be our own routing. | E17 | `test_route_elbow_textbook_cases` |
| F28 | SVG2 `inline-size` wraps text in Inkscape export (40 mm → 38.75 mm wide), but browser support is patchy → we wrap ourselves with measured word widths. | E17 | `test_wrap_to_width` |
| F29 | Transforms compose as expected for stamped rows: a shape with `matrix(-1,0,0,1,2X,0)` inside a `translate()` group measures exactly reflected (polygon 60..70 → 130..140); a reflected line keeps its marker on the reflected end; width-wrapping works inside transformed groups; a prepended `translate()` moves a transformed group as a block; native connectors attach to shapes in translated groups. | E21 | `test_repeat_timeline_with_mirroring` |
| F21 | With a non-zero viewBox origin, `query-all` positions are relative to the viewBox origin (px); adding the origin back gives user coordinates. | E11 | `test_page_fit_normalises_nonzero_viewbox_origin` |
| F30 | **Which id survives a path operation** (3 overlapping rects, both selection orders, E22): union, intersection, exclusion and difference keep the **bottom** object's id, style and parent; **combine keeps the top one's** (and its layer). Division and cut keep the bottom id and add new pieces (`path1`, …) with its style. The selection order doesn't matter. | E22, field report 7 | `test_path_operation_names_the_result` |
| F31 | Shell deaths: `file-close` with no document open prints `InkscapeApplication::close_document: No document!`. That happens on every `_open`, so the line in the field-report-5 crash was noise, not the cause. `quit` ends the process (stdout EOF), which simulates a crash. 200 iterations of the server's real cycle (wrap, anchor, fit, preview; thousands of shell commands) never killed the shell (E23). The field crash was the first command after ~28 idle minutes. Idle runs (E23b): the shell died once in 5 (after 930 s, while other Inkscape work ran in the same session), and survived 4, 5, 10 and 15 min. The dying shell still polls as alive; it dies on the next command, with exactly the field message. Other instances starting, quitting or being killed (E23c), and `uv run`/pytest in the foreground, didn't trigger it. **Cause unknown, rare, external** → retry and rollback (D-022). | E23, E23b, field report 5 | `test_a_pass_is_retried_when_the_shell_dies`, `test_shell_death_says_what_it_was_running` |
| F32 | **Clips** (`clip-path` → `clipPath clipPathUnits="userSpaceOnUse"`): `query-all` reports the **clipped** bbox. The clip shape is in the clipped element's own coordinates (including its transform), so a copy of a reference shape needs `transform = inv(CTM(el)) · CTM(ref)` to land exactly on it. When `transform-translate` moves the element, Inkscape rewrites its transform and the clip moves along. The clipPath survives Inkscape round trips. | E24 | `test_clip_to_a_panel_follows_the_element` |
| F33 | **Image links**: Inkscape resolves `file:///C:/…` URIs and `data:` URIs, but **not plain paths** (`C:\…` or `C:/…`: `URI::getContents failed`, which our stderr check turns into an error). Relative links would break anyway, because every operation opens a temp copy in another folder. PDF export embeds linked pixels. | E25 | `test_image_element_sizes_links_and_fits` |
| F34 | `<image>` honours `preserveAspectRatio` like browsers: `meet` letterboxes, `slice` crops (cover), `none` stretches. `query-all` reports the **viewport** box in every mode, not the painted area. Without width/height Inkscape sizes it at 1 user unit per pixel (a 200 px image is 200 mm wide in a mm document), so we always write a size (96 dpi). Inkscape 1.4 has no JPEG export. | E25 | same |
| F35 | **Page geometry of foreign files** (E30): `width="100%"` (or no width) is read as the **viewBox width** in px (the tiger: page 594 x 1123 px from `100%` / `297mm` / viewBox 594 x 840). When the viewBox's aspect differs from the page, Inkscape scales it **uniformly** and aligns it (`preserveAspectRatio`, default xMidYMid meet): a 100 x 100 viewBox in a 200 x 100 px page draws 100 x 100 px centred at x 50; `none` stretches per axis. `query-all` reports px on the page, so any model with one px-per-unit factor and no offset gets such files wrong. Moving that mapping onto the top-level elements' transforms renders pixel-identically in 3 of 4 cases; the tiger differs in 164 of 2.67 M channel values by at most 3/255 (anti-aliasing). Without a viewBox, a user unit is a px. | E30, field report 11 | `test_open_svgz_and_letterboxed_pages`, `test_stretched_page_keeps_its_shape` |
| F36 | `text-convert-to-regular` on a `flowRoot` (SVG 1.2 flowed text) **crashes Inkscape 1.4.4** (exit 3221225477, `flowtext_to_text()` in the stack); `object-flowtext-to-text` no longer exists. flowRoot can be moved and deleted but not converted in shell mode. | field report 11 | — (listed in the outline, not converted) |

## SVG behaviour

| # | Finding | Source | Guarded by |
|---|---|---|---|
| S1 | **Boolean ops drop presentation attributes** (`fill="…"`) → result turns black. `style="fill:…"` survives. Always write styles into `style`. | E01, E03 | `test_union_keeps_style`, `test_add_writes_style_attribute…` |
| S2 | Union result keeps the **bottom** object's id and style; the others are removed (combine is the exception: F30). | E01, E03 | `test_union_keeps_style` |
| S3 | Visual text bbox depends on glyphs: "Client" is 4.62 mm tall, "inksmcp" 6.0 mm (descender). Centring text by bbox ≠ centring by font metrics. | E06 | `test_centre_labels_in_boxes_share_baseline` |
| S4 | Text metrics scale exactly with font size (default sans: cap "H" = 0.714 em, "x" = 0.536 em, descender 0.240 em). But they **differ per font** (Arial 0.716, Times New Roman 0.694, Segoe UI 0.740…) → measure, don't assume. | E07, E07b | same |
| S5 | **Unknown font families silently fall back** to the default sans (identical metrics to `sans-serif`). No warning on stderr. | E07b | — (backlog: warn) |
| S6 | Inkscape honours `dominant-baseline` (central/middle/hanging) when measuring, but other renderers/PDF may not → we compute explicit `y` instead. | E07 | — |
| S7 | Markers render in headless PNG and PDF export. `orient="auto-start-reverse"` works; `fill:context-stroke` works in Inkscape PNG+PDF (but not all browsers → we use one marker per colour). | E09 | `test_connect_attaches_to_edges` |
| S8 | `query-all` bboxes of a path **include its markers** (line 70..180 → bbox 62..188). | E09 | — |
| S10 | A pointed marker with its tip at the path end leaves a **stub of the line visible beside the tip** (the stroke is wider than the tip near its point); moving refX back pokes the tip into the target. A **flat front one stroke-width wide** (`M 0,0 L 10,4 L 10,6 L 0,10 z`, refX=10) covers the line end exactly. | E17, field report 2 | `test_arrowheads_have_a_flat_front…` |
| S9 | Attributes in a custom namespace (`xmlns:inksmcp="urn:inksmcp"`) survive Inkscape SVG round-trips and plain-svg export. | E09 | `test_connector_label_sits_on_midpoint` |
| S11 | A text halo (`paint-order: stroke` + stroke) grows the measured bbox by the stroke width (half on each side): 2.4 mm stroke → +2.4 mm in width and height. | E24 | `test_text_halo_key` |
| S12 | **Root presentation paint is inherited by everything**: `<svg fill="none" stroke="rgb(0,0,0)">` (tiger) or `style="fill:black;stroke:black"` (NPS symbol library) gives every new element a black stroke. Symbol content inherits from the `use`, not from the symbol's parents, so a library symbol that relied on the root's stroke disappears when used elsewhere (the plain "Parking"). Pushing the properties onto the top-level children (and defs) renders the same. | E30, field report 11 | `test_open_svgz_and_letterboxed_pages`, `test_import_and_use_library_symbols` |

## inkex

`inkex` is **not** importable from Inkscape's bundled `python.exe` by default (it lives in
`share/inkscape/extensions`). Not needed so far: lxml + the shell cover everything (see D-005).
