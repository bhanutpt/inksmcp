# Plan / Roadmap

**Current phase:** Phase 3 — Power features (Phase 2 closed 2026-09-27, baseline in `08-benchmarks.md`)
**Last updated:** 2026-09-28

Method (D-003): experiment → finding (`05-inkscape-notes.md`) → test → code → docs.

## Phase 0 — Planning & docs ✅
- [x] Create docs skeleton
- [x] Initialize git repository
- [x] Choose implementation language & MCP SDK → Python, `mcp` 2.x (D-002)
- [x] Spike the Inkscape CLI / shell (E01–E05) → findings F1–F11, S1–S3
- [x] Decide integration strategy → lxml source of truth + persistent shell (D-004)

## Phase 1 — Foundations (MVP) ✅
- [x] uv project, pytest
- [x] Inkscape locator + version
- [x] Persistent shell driver with stderr error detection
- [x] Document create / open / save
- [x] Inspect with real bboxes in user units
- [x] Batch element add / update / delete, layers, text
- [x] Path operations, guarded raw actions
- [x] Export (sticky-state safe) and render preview
- [x] End-to-end over stdio (E06)
- [x] Register with Claude Code (project `.mcp.json`, 2026-09-27)
- [x] Use it for real work in a Claude session and log what the agent struggles with (field tests, `docs/field-reports/`)

## Phase 2 — Agent-load reducers (from E06 observations) ✅
- [x] `align` — batch, cap-box text centring, as_group, margin (E07, E08, D-007)
- [x] `connect` — native connectors, markers, labels (E09, E09b, D-008)
- [x] `layout` — row / column / grid, items as units, off-page warnings (E10, D-009)
- [x] `page_fit` / `page_resize` (E11, E12, D-010)
- [x] z-order + move to layer (E13, D-011)
- [x] Field test 1 in a separate agent session: A4 log-log graph paper → report, all follow-ups done (E15, E16, D-012–D-014)
- [x] Field test 2: A4 heat-pump poster → report; follow-ups done (E17, E18, D-015–D-017)
- [x] Field test 3: A3 flight-history infographic → report recorded 2026-09-27 (26 calls, no errors). Cheap follow-ups done (E19, D-018: per-axis gridlines, series ids, label halo/anchor). Open: `repeat`/template stamping, rect `fit_to` text, bar series + category axis in `plot`, export bleed/crop marks
- [x] Measure: tool calls & tokens for a reference set of tasks → `08-benchmarks.md` (E20): 4–8 calls and 0.4k–1.9k tokens per task; the tool list (≈ 6.3k tokens) costs more than any task

## Phase 3 — Power features
- [ ] Gradients, patterns, markers in defs
- [ ] Import images / other SVGs
- [ ] Field test 4: images (e.g. an event flyer with a photo, or a labelled product sheet) — needs image import
- [ ] Templates & reusable components
  - [x] `repeat`: a block of specs stamped per data row, with step/columns and alternate mirroring (E21, D-019, F29). E20 timeline: 3,002 → 1,887 request chars
  - [x] rect `fit_to` + padding: card height from its content (D-020). E20 timeline back to 4 calls, 1,749 request chars
- [ ] Field-test round 2 (D-021): run several varied tasks first, then synthesise common vs task-specific needs before building
  - [x] Tamil alphabet A3 poster (2026-09-28): 13 calls, no errors; needs recorded in its report's "Common or task-specific?" table
  - [ ] More tasks (ideas: comic panel page, flash cards / worksheet, org chart, map / floor plan, certificate)
  - [ ] Synthesis: merge the tables across reports, rank by frequency × saved rework, then experiment → test → code
- [ ] Snapshots / undo
- [ ] Resources: document SVG, action list

## Phase 4 — Polish
- [ ] Keep document open in shell between Inkscape ops (perf, D-004)
- [ ] Trim tool schemas/descriptions (E20: tool list ≈ 6.3k tokens; `connect` alone 4.2k chars) and re-run the benchmark
- [ ] Packaging & install instructions for other machines / OSes
- [ ] CI (needs Inkscape in the runner)

## Open questions
- Should `inspect` support filtering (by layer / id prefix) for big documents?
- How to present fonts: list installed fonts? verify availability?
