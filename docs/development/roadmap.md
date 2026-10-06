# Plan / Roadmap

**Current phase:** Phase 3 — Power features (Phase 2 closed 2026-09-27, baseline in `benchmarks.md`); release 0.3.0 prepared 2026-09-28, tagged 2026-10-06 after the first release run failed its tests (first public release, see `releasing.md`)
**Last updated:** 2026-10-06

Method (D-003): experiment → finding (`inkscape-notes.md`) → test → code → docs.

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
- [x] Use it for real work in a Claude session and log what the agent struggles with (field tests, `docs/development/field-reports/`)

## Phase 2 — Agent-load reducers (from E06 observations) ✅
- [x] `align` — batch, cap-box text centring, as_group, margin (E07, E08, D-007)
- [x] `connect` — native connectors, markers, labels (E09, E09b, D-008)
- [x] `layout` — row / column / grid, items as units, off-page warnings (E10, D-009)
- [x] `page_fit` / `page_resize` (E11, E12, D-010)
- [x] z-order + move to layer (E13, D-011)
- [x] Field test 1 in a separate agent session: A4 log-log graph paper → report, all follow-ups done (E15, E16, D-012–D-014)
- [x] Field test 2: A4 heat-pump poster → report; follow-ups done (E17, E18, D-015–D-017)
- [x] Field test 3: A3 flight-history infographic → report recorded 2026-09-27 (26 calls, no errors). Cheap follow-ups done (E19, D-018: per-axis gridlines, series ids, label halo/anchor). Open: `repeat`/template stamping, rect `fit_to` text, bar series + category axis in `plot`, export bleed/crop marks
- [x] Measure: tool calls & tokens for a reference set of tasks → `benchmarks.md` (E20): 4–8 calls and 0.4k–1.9k tokens per task; the tool list (≈ 6.3k tokens) costs more than any task

## Phase 3 — Power features
- [ ] Gradients, patterns, markers in defs — plus a colour summary in `inspect` and recolouring that follows gradient stops (field report 12: the car)
- [x] Import images / other SVGs (round-2 step 1, D-026)
- [ ] Field test 4: images (e.g. an event flyer with a photo, or a labelled product sheet) — needs image import
- [ ] Templates & reusable components
  - [x] `repeat`: a block of specs stamped per data row, with step/columns and alternate mirroring (E21, D-019, F29). E20 timeline: 3,002 → 1,887 request chars
  - [x] rect `fit_to` + padding: card height from its content (D-020). E20 timeline back to 4 calls, 1,749 request chars
- [ ] Field-test round 2 (D-021): run several varied tasks first, then synthesise common vs task-specific needs before building
  - [x] Tamil alphabet A3 poster (2026-09-28): 13 calls, no errors; needs recorded in its report's "Common or task-specific?" table
  - [x] Comic page "The Last Cookie" (2026-09-28): 18 calls; one intermittent shell crash left a half-applied batch (bug, fix now)
  - [x] Periodic table A3 poster (2026-09-28): 17 calls, 590-element `repeat`, no crash
  - [x] 2 BHK floor plan A4 (2026-09-28): 16 calls, scaled-group metres, poché via path operations
  - [x] OSM route map A3 (2026-09-28): 18 calls; geometry via script + `document_open` (no import into a document yet)
  - [x] Swimlane flowchart A4 (2026-09-28): 18 calls, no external scripts, `connect` did all routing
  - [x] Datasheet page A4, 4 plots (2026-09-28): ~41 calls; layout aligns bboxes not plot frames
  - [x] Fix: `grid` lines classed by index, non-nesting spacings rejected; log labels follow `start` (datasheet report; D-023)
  - [x] Fix: `path_operation` returns `result`; combine keeps the top id, now documented (floor-plan report; E22, F30)
  - [x] Fix: every tool all-or-nothing + one retry on a dead shell (comic report; E23–E23c, F31, D-022). Crash reproduced once in 5 idle runs, cause still unknown
  - [x] Synthesis: [round-2 synthesis](field-reports/2026-09-28-round-2-synthesis.md), reviewed 2026-09-28 (D-024)
- [ ] Round-2 build (D-024), each step experiment → test → code:
  - [x] Step 0 (2026-09-28): compact `repeat` response, `id_prefix` clash error, `order: column`, connector layers + label ids + gaps, descriptions, `clip` and text `halo` keys (E24, F32, S11, D-025). Inspect child bboxes → step 2 warnings
  - [x] Step 1 (2026-09-28): `image` element, `import_file` (SVG/images), `elements_path` / `rows_path` (E25, E26, F33, F34, D-026). E26: 51 kB map geometry in 7 calls
  - [x] Step 2 (2026-09-28): automatic overlap warnings (stacks reported once), stored `place` settled with `fit_to` in one order, `layout` anchors (E27, D-027)
  - [x] Step 3 (2026-09-28): `repeat` `cell`, `split` tool; no table element — `split` + `repeat` recipe covers it (E28, D-028)
  - [ ] Step 4: components (update by template name, anchors, callout `tail_to`), style maps + legends
  - [ ] Field tests after steps 0–3: org chart, certificate, worksheet / flash cards, image flyer (field test 4)
    - [x] Comic page 2 (2026-09-28): 27 calls, no errors; 15 false overlap warnings → fixed (E29, D-029)
  - [x] Field test 11, editing foreign SVGs (2026-09-28, fresh subagent): 12 bugs → fixed (E30, D-030). Success criterion 2 now has a test
- [ ] Snapshots / undo
- [ ] Resources: document SVG, action list

## Phase 4 — Polish
- [ ] Keep document open in shell between Inkscape ops (perf, D-004)
- [ ] Trim tool schemas/descriptions (E20: tool list ≈ 6.3k tokens; `connect` alone 4.2k chars) and re-run the benchmark
- [x] Packaging & install instructions for other machines / OSes (2026-09-28: PyPI metadata, `uvx inksmcp`, `server.json`, getting started per OS; D-031)
- [x] CI (needs Inkscape in the runner): Linux (PPA + Liberation fonts + xvfb), Windows (choco), macOS (brew)
- [x] Release workflow: tag → tests → PyPI (trusted publishing) → GitHub release + MCP Registry; `scripts/bump_version.py`, `scripts/release_notes.py`
- [x] User docs: getting started, recipes (run by the tests), tool reference generated from the server
- [ ] Publish 0.3.0: create the GitHub repo, PyPI pending publisher, push, tag (maintainer steps in `releasing.md`)
- [x] Re-run field test 11's jobs on the fixed build with a fresh agent: field report 12, follow-ups fixed (D-032)
- [x] CI green on Linux, Windows, macOS (2026-09-28, run 36406984989; the first runs found the wrap overflow F38, font-dependent tests and the Chocolatey shim F39)

## Open questions
- Should `inspect` support filtering (by layer / id prefix) for big documents?
- How to present fonts: list installed fonts? verify availability?
