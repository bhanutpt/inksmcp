# Plan / Roadmap

**Current phase:** Phase 0 — Planning & docs
**Last updated:** 2026-09-27

## Phase 0 — Planning & docs
- [x] Create docs skeleton
- [x] Initialize git repository
- [ ] Choose implementation language & MCP SDK (see `06-decisions.md`)
- [ ] Spike: drive Inkscape CLI (`--actions`, `--export-*`, `--shell`) and record findings in `05-inkscape-notes.md`
- [ ] Decide integration strategy (SVG-direct vs Inkscape CLI vs hybrid)

## Phase 1 — Foundations (MVP)
- [ ] Project scaffold, lint, test runner
- [ ] Inkscape locator + version check
- [ ] Document open / create / save
- [ ] Document inspection (tree summary)
- [ ] Export (PNG, PDF, SVG)
- [ ] Render preview for the AI to see
- [ ] Register server with an MCP client and test end-to-end

## Phase 2 — Core editing
- [ ] Shapes: rect, ellipse, line, path, polygon
- [ ] Text
- [ ] Styling: fill, stroke, opacity, fonts
- [ ] Layers & groups
- [ ] Transforms: move, scale, rotate, align/distribute
- [ ] Selection by id / query

## Phase 3 — Power features
- [ ] Inkscape actions: boolean ops, path simplify, object-to-path, text-to-path
- [ ] Gradients, patterns, markers
- [ ] Import images / other SVGs
- [ ] Templates & reusable components
- [ ] Undo/history (snapshots)

## Phase 4 — Polish
- [ ] Performance (long-running Inkscape shell process?)
- [ ] Error messages tuned for AI consumption
- [ ] Packaging & install instructions
- [ ] TBD

## Open questions
- Keep one persistent Inkscape process (`--shell`) or spawn per call?
- How much can be done by editing SVG XML directly vs needing Inkscape itself?
- How should documents be referenced across calls (path, handle/session id)?
