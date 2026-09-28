# Changelog

All notable changes to this project. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## Unreleased

## 0.3.0 — 2026-09-28

First public release. Round-2 build from ten field reports, editing of files made elsewhere, and release packaging:
24 tools, 159 tests against the real Inkscape.

### Added
- 2026-09-28 — Release packaging: MIT license, PyPI metadata (`uvx inksmcp`), `server.json` for the MCP Registry, CI on Linux, Windows and macOS, a tag-triggered release workflow (PyPI trusted publishing, GitHub release, registry), user docs (getting started, recipes, a tool reference generated from the server), contributing and security notes. Development docs moved to `docs/development/`.
- 2026-09-28 — Editing files made elsewhere (D-030, experiment e30): `document_open` normalises page geometry (%, mismatched or offset viewBoxes, stretched pages) and root paint without changing the rendering, and says so in `notes`; `.svgz` open/save; `inspect` shows computed fill/stroke, `use` targets, flowed text and symbols, and `find` lists matches by type, colour, text, href or id prefix; `use` element type (`library.svg#symbol` copies a symbol in once); deleting elements removes defs only they used. 6 new tests (140 total).
- 2026-09-28 — Round-2 step 3 (D-028): `repeat` `cell` (rows placed by their own column/row numbers) and the `split` tool (a region divided into named cell rects by column ratios, height ratios and gutters). Tables are a documented `split` + `repeat` recipe. Experiment e28. 3 new tests (132 total).
- 2026-09-28 — Round-2 step 2 (D-027): automatic overlap warnings in editing responses (text on text, text across a shape edge, un-haloed text crossed by a line; stacked elements reported once); `place` key (stored below/above/left_of/right_of + gap + align, re-applied with `fit_to` in one dependency order, also after align/layout moves of the reference); `layout` items with an `anchor`. Experiment e27. 6 new tests (129 total).
- 2026-09-28 — Round-2 step 1, files in (D-026): `image` element (linked or embedded, natural size, `object_fit`), `import_file` tool (SVG as one scaled group with renamed ids and fixed references; images), `add_elements` `elements_path` and `repeat` `rows_path` (JSON/CSV). Experiments e25, e26; findings F33, F34. 4 new tests (123 total).
- 2026-09-28 — Round-2 step 0 (D-025): `clip` key on any element (element id or rect; clipped bbox; follows the element), text `halo` / `halo_width`, connector `start_gap` / `end_gap`, connectors placed in their ends' layer or a "Connectors" layer with `layers` and `labels` in the response, `repeat` `order: "column"`, shortened id runs in `repeat` responses, `id_prefix` clash error, clearer `repeat` / `align` / element descriptions. Experiment e24; findings F32, S11. 6 new tests (119 total).
- 2026-09-28 — `path_operation` returns `result`: the ids holding the outcome (combine keeps the top id, the other boolean ops the bottom one; E22, F30).
- 2026-09-28 — `grid` log axes: `labels: "decades" | "paper"`; decade labels follow `start` by default when it is given (D-023).
- 2026-09-27 — rect `fit_to` / `fit_padding` / `fit`: a box sized around other elements after wrapping, re-fitted when they are edited, chained in dependency order, usable in `repeat` templates. Decision D-020. 4 new tests (103 total).
- 2026-09-27 — `repeat` tool: stamp a template per data row (placeholders, local ids, step/columns, alternate mirroring that reflects shapes and moves texts/groups as blocks, off-page warnings, all or nothing). Experiment e21; finding F29; decision D-019. E20 timeline: 37 % less request text. 3 new tests (99 total).

### Fixed
- 2026-09-28 — From field report 12 (re-run on 0.3.0) and the first CI run: text wrapped with `width` could overflow by up to 2.3 % in fonts other than Arial (lines are now measured, F38); `use` ignored width/height for symbols without a viewBox and drew library icons in the wrong units; `run_actions` extensions silently changed the whole drawing when `select` was given (now refused, F37); saved files reopened with a rounding "normalisation"; `find text` missed flowed text past 160 characters. `document_save` reports bytes, PNG exports their pixel size. 9 new tests (159 total).
- 2026-09-28 — From field report 11 (editing Inkscape's own sample files): `.svgz` could not be opened and unexpected errors reached the agent as an empty "Error executing tool"; pages whose viewBox didn't match their size were measured wrongly and `page_fit` wrote a non-uniform scale; `import_file` dropped the source root's fill/stroke, could stretch, and numbered id-less elements differently from `document_open`; `place` reported the move instead of the box; `sodipodi:docname` kept a temp name; the `defaults` error blamed every key when `type` was the problem; `find`-style lookups skipped elements at random (unstable proxy ids).
- 2026-09-28 — Overlap warnings no longer flag shapes hidden under a text's opaque balloon or caption box (comic page 2: 15 false warnings → 0), and findings are grouped per text (D-029, experiment e29). 2 new tests (134 total).
- 2026-09-28 — A crash of the Inkscape shell part-way through a tool left the document half-changed (e.g. elements written but not wrapped/fitted). Every tool now restores the document on failure, and a dead shell is retried once (E23, D-022). Errors name the exit code and command. 10 new tests (113 total).
- 2026-09-28 — `grid` silently dropped major lines and labels when `major` was a rounded multiple of `minor` (11.6667 / 2.3333); spacings that don't nest are now an error (D-023). `plot` no longer warns about edge points a hair outside.
- 2026-09-28 — `path_operation` described combine's surviving id wrongly.
- 2026-09-27 — The element help in the `add_elements` description showed a garbled em dash (`â€”`).
- 2026-09-27 — `vertical_anchor` placed texts inside transformed groups or layers wrongly: it compared the local `y` with document-space measurements.

## 0.2.0 — 2026-09-27

Phase 1 (MVP) and Phase 2 (agent-load reducers): 21 tools, three field tests, benchmark baseline in `docs/development/benchmarks.md`.

### Added
- 2026-09-27 — Reference benchmark (experiment e20, `docs/development/benchmarks.md`): calls, request/response size, image tokens and time for 5 tasks, plus tool-list size. Phase 2 baseline: 4–8 calls, 0.4k–1.9k tokens per task; tool list ≈ 6.3k tokens.
- 2026-09-27 — From field report 3 (flight infographic), cheap follow-ups: `plot` child ids follow the series id, `label_halo` and `label_anchor` options, label placement and halo documented; `grid` axis `"lines": false`; `bold_major` documented. Experiment e19; decision D-018. 2 new tests (96 total).
- 2026-09-27 — From field report 2 (heat-pump poster): `plot` tool and `grid` axis titles; connector `from_side`/`to_side`/`via` (own router, stays attached), label position/side/offset/font/halo; `marker_start`/`marker_end` on lines/paths; `arrow` element; text `width` wrapping; `move_to_layer` position. Experiments e17, e18; findings F26–F28, S10; decisions D-015–D-017. 13 new tests (94 total).
- 2026-09-27 — From field report 1 (log graph paper): `grid` tool (linear/log axes, weight classes, border, measured labels); `render_preview` `region` and zoom-by-ids; `export` `region`/`only_ids`; `add_elements` `defaults`; text `vertical_anchor`. Experiments e15, e16, e16b; findings F23–F25; decisions D-012–D-014. 9 new tests (81 total).
- 2026-09-27 — `z_order` (front/back/above/below exact; forward/backward overlap-based) and `move_to_layer`; cross-parent moves keep the visual position via affine compensation (`layout.py`).
- 2026-09-27 — Experiment e13; finding F22; decision D-011; `docs/development/field-reports/`. 9 new tests (70 total).
- 2026-09-27 — `inspect` summarises layers/groups with many children and supports `layer` drill-down (E14: 30,806 → 600 chars). 2 new tests (72 total).
- 2026-09-27 — `page_fit` (drawing or ids + margin, origin kept at 0,0, backgrounds resized, connectors follow) and `page_resize` (exact size, anchor top-left/center, off-page warnings).
- 2026-09-27 — Moves snapped to 0.001 user units and moved elements tidied to 4 decimals (no more `20.000042`).
- 2026-09-27 — Experiments e11, e12; findings F18–F21; decision D-010. 12 new tests (61 total).

### Fixed
- 2026-09-27 — Multi-line text had a doubled first line gap and ignored `line_height` (F26); indents were collapsed.
- 2026-09-27 — A strip of the line showed past arrowhead tips (S10): flat-front arrowheads.
- 2026-09-27 — `render_preview`/`export` with several ids produced nothing (`export-id` takes one id, F23); "was not found" warnings now raise.
- 2026-09-27 — Shell work batched: grid with 74 labels 11.2 s → 1.2 s; test suite 22.7 s → 14.5 s (F25).
- 2026-09-27 — Connectors passed to a move (directly or as top-level content) were moved twice (F20).
- 2026-09-27 — `connect` tool: native Inkscape connectors (straight/elbow), per-colour arrow markers, midpoint labels with halo, warnings for text endpoints; connectors re-sync after `update_elements`; `delete_elements` cascades to attached connectors and labels.
- 2026-09-27 — `layout` tool: row/column/grid, items as id lists moved together, block placement (`at` / `to` + align).
- 2026-09-27 — Off-page warnings from `align` and `layout`.
- 2026-09-27 — Experiments e09, e09b, e10; findings F15–F18, S7–S9; decisions D-008, D-009. 13 new tests (49 total).
- 2026-09-27 — `align` tool: batch alignment to page / selection / element, `as_group`, `margin`; text centred by measured cap box so labels share baselines. New `layout.py` (pure maths), `Engine.measure` / `translate` / `align`. 10 new tests.
- 2026-09-27 — Experiments e07, e07b, e08; findings F12–F14, S4–S6; decision D-007.
- 2026-09-27 — Registered the server for Claude Code via project `.mcp.json`.
- 2026-09-27 — Phase 1 MVP: persistent Inkscape shell driver, lxml document model, Inkscape-backed engine, MCP server with 12 tools (`inkscape_info`, `document_create/open/save`, `inspect`, `add/update/delete_elements`, `path_operation`, `run_actions`, `export`, `render_preview`).
- 2026-09-27 — Test suite (26 tests) against real Inkscape, incl. end-to-end via in-process MCP client.
- 2026-09-27 — Experiments e01–e06 and findings F1–F11, S1–S3 in `docs/development/inkscape-notes.md`.
- 2026-09-27 — Decisions D-002…D-006; lessons learned; experiment-driven workflow in `docs/development/README.md`.
- 2026-09-27 — Initial docs skeleton: objectives, plan, architecture, features, Inkscape notes, decision log, lessons learned.
- 2026-09-27 — Git repository initialized.
