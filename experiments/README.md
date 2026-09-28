# Experiments

Small, runnable probes of real Inkscape behaviour. Each one answers a question; its answer is
recorded in [`docs/development/inkscape-notes.md`](../docs/development/inkscape-notes.md) and, if the code relies on
it, guarded by a test in `tests/`.

Run with `uv run python experiments/<file>.py`. Outputs go to `experiments/out/` (git-ignored).

| # | Question | Findings |
|---|---|---|
| e01 | How do export, query and action chains behave? Error reporting? | F1, S1, S2, timings |
| e02 | Does `--shell` work as a persistent process? Protocol? Latency? | F2, F3 |
| e03 | Does `style=""` survive boolean ops? Is inkex available? | S1, inkex note |
| e04 | Query units in mm docs, layer survival, missing files | F4, F8 |
| e05, e05b, e05c | Are export options sticky? How to reset? | F5, F6, F10 |
| e06 | Real usage over stdio: build a diagram as an agent would | S3, perf, Phase 2 backlog |
| e07 | Does `object-align` work headless? translate units? font metrics? dominant-baseline? | F12, F13, S4, S6 |
| e07b | Do generic font families differ? Unknown fonts? translate dy direction | S4, S5, F13 |
| e08 | Real usage: rebuild e06 with `align` — how much agent work disappears? | F14, D-007 |
| e09 | Markers in export? context-stroke? native connectors? custom attrs survive? | F15, S7–S9 |
| e09b | Native connectors: routing on load, circles, groups, text, orthogonal | F15–F17 |
| e10 | Real usage: flowchart from relationships only (layout/align/connect) | D-009 |
| e11 | `page-fit-to-selection` headless? backgrounds? non-zero viewBox origin? | F18, F21 |
| e12 | Real usage: fix an off-page flowchart with one `page_fit`; coordinate noise | F14, D-010 |
| e13 | Z-order actions: raise vs stack-up, top/bottom in layers, multi-selection | F22, D-011 |
| e14 | Scale: 325 elements in one call, inspect size, A4 300 dpi export | perf table, inspect summaries |
| e15 | Field report bugs: several export ids? export-area units? | F23, F24, D-012 |
| e16 | Redo field test 1 with `grid` + region zoom (14 → 6 calls) | D-013 |
| e16b | Shell batching: per-line vs joined line vs one selection | F25, D-014 |
| e17 | Field report 2: multi-line text layout, arrow stub, connection points, inline-size | F26–F28, S10 |
| e18 | Redo field test 2's hard parts with sides/arrow/width/plot (31 → 8 calls) | D-015–D-017 |
| e19 | Field test 3's bar chart with x-only gridlines, series ids, halo-free inside labels (5 calls, no fixes) | D-018 |
| e21 | `repeat` mechanics: reflected shapes/markers in translated groups, wrapping, block moves, connectors | F29, D-019 |
| e22 | Which id survives each path operation (order, layers)? | F30 |
| e23, e23b, e23c | Can the field-report-5 shell crash be reproduced (stress loop; idle shell; other Inkscape instances)? | F31, D-022 |
| e24 | Clip mechanics (clipped bbox, transformed groups, moves, round trips) and text halo bbox growth | F32, S11, D-025 |
| e25 | Image mechanics: href forms, preserveAspectRatio, sizes, JPEG export | F33, F34, D-026 |
| e26 | Real usage: 51 kB geometry file + CSV labels + photo inset through the tools (7 calls) | D-026 |
| e27 | Real usage for step 2: Tamil card placement, map label collisions, flowchart false positives, plot frames by anchor | D-027 |
| e28 | Real usage for step 3: comic panel grid, periodic-table cells from CSV, a table from split + repeat | D-028 |
| e29 | Overlap warnings on nine finished pages: which are hidden under an opaque box (comic page 2 report) | D-029 |
| e30 | Foreign files: .svgz, page geometry Inkscape uses for % / mismatched viewBoxes, rendering before/after normalising, ids on open vs import | F35, S12, D-030 |
| e31 | Do extension actions honour the selection in shell mode? | F37, D-032 |
| e20 | Reference benchmark: calls/tokens for flowchart, graph paper, bar chart, icon, timeline; tool-list size | `08-benchmarks.md` |
