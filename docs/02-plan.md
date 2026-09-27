# Plan / Roadmap

**Current phase:** Phase 2 — Agent-load reducers
**Last updated:** 2026-09-27

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
- [ ] Use it for real work in a Claude session and log what the agent struggles with

## Phase 2 — Agent-load reducers (from E06 observations)
- [x] `align` — batch, cap-box text centring, as_group, margin (E07, E08, D-007)
- [ ] `connect` — arrows between elements with markers
- [ ] `layout` — row / column / grid with gaps
- [ ] z-order
- [ ] Measure: tool calls & tokens for a reference set of tasks (diagram, poster, icon)

## Phase 3 — Power features
- [ ] Gradients, patterns, markers in defs
- [ ] Import images / other SVGs
- [ ] Templates & reusable components
- [ ] Snapshots / undo
- [ ] Resources: document SVG, action list

## Phase 4 — Polish
- [ ] Keep document open in shell between Inkscape ops (perf, D-004)
- [ ] Packaging & install instructions for other machines / OSes
- [ ] CI (needs Inkscape in the runner)

## Open questions
- Should `inspect` support filtering (by layer / id prefix) for big documents?
- How to present fonts: list installed fonts? verify availability?
