# Changelog

All notable changes to this project. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## Unreleased

### Added
- 2026-09-27 — `page_fit` (drawing or ids + margin, origin kept at 0,0, backgrounds resized, connectors follow) and `page_resize` (exact size, anchor top-left/center, off-page warnings).
- 2026-09-27 — Moves snapped to 0.001 user units and moved elements tidied to 4 decimals (no more `20.000042`).
- 2026-09-27 — Experiments e11, e12; findings F18–F21; decision D-010. 12 new tests (61 total).

### Fixed
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
