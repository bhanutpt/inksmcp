# Changelog

All notable changes to this project. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## Unreleased

### Added
- 2026-09-27 — rect `fit_to` / `fit_padding` / `fit`: a box sized around other elements after wrapping, re-fitted when they are edited, chained in dependency order, usable in `repeat` templates. Decision D-020. 4 new tests (103 total).
- 2026-09-27 — `repeat` tool: stamp a template per data row (placeholders, local ids, step/columns, alternate mirroring that reflects shapes and moves texts/groups as blocks, off-page warnings, all or nothing). Experiment e21; finding F29; decision D-019. E20 timeline: 37 % less request text. 3 new tests (99 total).

### Fixed
- 2026-09-27 — The element help in the `add_elements` description showed a garbled em dash (`â€”`).
- 2026-09-27 — `vertical_anchor` placed texts inside transformed groups or layers wrongly: it compared the local `y` with document-space measurements.

## 0.2.0 — 2026-09-27

Phase 1 (MVP) and Phase 2 (agent-load reducers): 21 tools, three field tests, benchmark baseline in `docs/08-benchmarks.md`.

### Added
- 2026-09-27 — Reference benchmark (experiment e20, `docs/08-benchmarks.md`): calls, request/response size, image tokens and time for 5 tasks, plus tool-list size. Phase 2 baseline: 4–8 calls, 0.4k–1.9k tokens per task; tool list ≈ 6.3k tokens.
- 2026-09-27 — From field report 3 (flight infographic), cheap follow-ups: `plot` child ids follow the series id, `label_halo` and `label_anchor` options, label placement and halo documented; `grid` axis `"lines": false`; `bold_major` documented. Experiment e19; decision D-018. 2 new tests (96 total).
- 2026-09-27 — From field report 2 (heat-pump poster): `plot` tool and `grid` axis titles; connector `from_side`/`to_side`/`via` (own router, stays attached), label position/side/offset/font/halo; `marker_start`/`marker_end` on lines/paths; `arrow` element; text `width` wrapping; `move_to_layer` position. Experiments e17, e18; findings F26–F28, S10; decisions D-015–D-017. 13 new tests (94 total).
- 2026-09-27 — From field report 1 (log graph paper): `grid` tool (linear/log axes, weight classes, border, measured labels); `render_preview` `region` and zoom-by-ids; `export` `region`/`only_ids`; `add_elements` `defaults`; text `vertical_anchor`. Experiments e15, e16, e16b; findings F23–F25; decisions D-012–D-014. 9 new tests (81 total).
- 2026-09-27 — `z_order` (front/back/above/below exact; forward/backward overlap-based) and `move_to_layer`; cross-parent moves keep the visual position via affine compensation (`layout.py`).
- 2026-09-27 — Experiment e13; finding F22; decision D-011; `docs/field-reports/`. 9 new tests (70 total).
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
- 2026-09-27 — Experiments e01–e06 and findings F1–F11, S1–S3 in `docs/05-inkscape-notes.md`.
- 2026-09-27 — Decisions D-002…D-006; lessons learned; experiment-driven workflow in `docs/README.md`.
- 2026-09-27 — Initial docs skeleton: objectives, plan, architecture, features, Inkscape notes, decision log, lessons learned.
- 2026-09-27 — Git repository initialized.
