# Experiments

Small, runnable probes of real Inkscape behaviour. Each one answers a question; its answer is
recorded in [`docs/05-inkscape-notes.md`](../docs/05-inkscape-notes.md) and, if the code relies on
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
| e10 | Real usage: flowchart from relationships only (layout/align/connect) | F18, D-009 |
