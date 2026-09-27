# Lessons learned

Things that surprised us, cost time, or made us faster. Keep each entry short and actionable.

## Template

```
### YYYY-MM-DD — <short title>
- What happened:
- Why:
- What we do now:
```

---

### 2026-09-27 — Never trust Inkscape's exit code
- What happened: Failed actions, missing ids and missing files all returned `rc=0`.
- Why: Inkscape treats action failures as warnings on stderr.
- What we do now: `InkscapeShell.run` classifies stderr lines and raises `InkscapeError`.

### 2026-09-27 — Shell state is global and sticky
- What happened: After one `export-id`, every later export in the session was cropped to that object, even after reopening the file.
- Why: Export options live on the application, not the document.
- What we do now: Every export sends the full `EXPORT_BASELINE` plus exactly one area mode. A regression test runs exports in mixed order.

### 2026-09-27 — A test failure was an experiment
- What happened: The first export test failed with a page-sized image when exporting by id.
- Why: `export-area-page` wins over `export-id` (F7).
- What we do now: Treat surprising test failures as findings — record them in the notes, don't just patch.

### 2026-09-27 — Check the installed SDK, not memory
- What happened: `from mcp.server.fastmcp import FastMCP` failed; mcp 2.x renamed it to `MCPServer` and hides exception messages unless you raise `ToolError`.
- What we do now: Inspect the installed package (`inspect.signature`, source) before writing integration code.

### 2026-09-27 — Presentation attributes are fragile
- What happened: A boolean union turned a blue/orange shape black.
- What we do now: The document layer always writes `style="…"` and folds any `fill=`-style attributes into it on update.

### 2026-09-27 — Real usage shows what the agent is still computing
- What happened: Building a 3-box diagram (E06) needed only 8 tool calls, but the "agent" still hand-computed box positions, text baselines for vertical centring, and arrow endpoints — and arrows had no heads.
- What we do now: Those become the next features (layout, align-to, connectors). See `04-features.md`.

### 2026-09-27 — Measure with probes instead of modelling fonts
- What happened: Centring text needs font metrics, which differ per font (S4) and fall back silently (S5).
- What we do now: Clone the text into a scratch copy of the document with every line replaced by "H" and let Inkscape measure it. Same parent, same inherited style, same transforms → exact numbers with zero font code. Reusable trick for any "how big would this be?" question.

### 2026-09-27 — Suspicious equality is a finding
- What happened: `serif` and `sans-serif` gave identical metrics in E07. A follow-up (E07b) showed generic families do differ, but the test string's ascender masked it; it also revealed that unknown fonts fall back silently.
- What we do now: When two things that should differ measure the same, run one more small experiment before building on it.

### 2026-09-27 — `align` removed the agent's arithmetic (E06 → E08)
- E06: agent computed 9 positions and guessed text baselines. E08: elements dropped at 0,0, one `align` call with 5 operations → centred row, labels on one baseline, title 20 mm from top.
- Takeaway: the best tools accept *relationships* ("centre in box", "20 mm from top") instead of coordinates.

### 2026-09-27 — Look for the native feature before building one
- What happened: We planned our own arrow routing. E09 showed Inkscape's connectors re-route headless, clip to real shapes and stay live in the GUI.
- What we do now: Before designing an abstraction, grep `--action-list` and test the native SVG/Inkscape mechanism first. Wrap it; only fill its gaps (text endpoints, labels, marker colours).

### 2026-09-27 — Previews don't catch everything; tell the agent in words
- What happened: In E10 a box ran 16 mm off the page. The preview showed it cut off, but an agent skimming an image easily misses that.
- What we do now: Tools return explicit `warnings` for things an agent should act on (off-page, text endpoints). Cheap to compute from boxes we already measured.

### 2026-09-27 — Flowchart from relationships only (E10)
- 12 elements, 6 connectors (labelled, dashed, elbow) in 8 tool calls, zero coordinates except shape sizes. The agent never computed a position.

### 2026-09-27 — Features interact; test the combinations
- What happened: `page_fit` alone worked, `connect` alone worked, but together a top-level connector was moved twice (F20). Only a test that combined them caught it.
- What we do now: Each new tool gets at least one test combined with each earlier "stateful" feature (connectors, layers, backgrounds).

### 2026-09-27 — Weak assertions hide knowledge
- What happened: A first test accepted "layer has a transform OR the route shifted". Pinning it to the observed behaviour (`translate(-35,-25)`, route unchanged) also exposed the measurement noise (`-34.999973`) that led to snapping moves.
- What we do now: When unsure what Inkscape will do, observe first, then assert exactly that.

### 2026-09-27 — Inkscape's verbs are visual, not structural
- What happened: "Raise one step" skipped non-overlapping siblings and did nothing when nothing overlapped (E13). Page-fit moved content instead of the viewBox (E11).
- What we do now: Name tools after the *outcome* the agent wants, and choose per operation whether the structural (lxml) or visual (Inkscape) meaning fits. Say so in the tool description.

### 2026-09-27 — Agent context is a resource; measure tool output size
- What happened: A scale probe (E14) showed `inspect` returning 30k characters for a 325-line grid — one call would eat a large part of an agent's context.
- What we do now: Experiments print the size of every tool response. Big containers are summarised (counts, first/last ids, bbox); the agent can drill into one layer on request.

### 2026-09-27 — A separate agent session finds what our own trials can't
- What happened: The first field test (log graph paper) hit a bug our tests never touched (multi-id preview), a semantic mismatch (ids = isolate vs zoom), and a whole missing tool class (scales/grids). Our scripted trials were shaped by our own assumptions.
- What we do now: After each feature batch, run a field test with a realistic task in a fresh session; turn its report into experiments, tests and tools; mark the report's follow-ups as done.

### 2026-09-27 — Scaling a feature exposes per-call overheads
- What happened: `grid` worked but took 11 s — label anchoring issued 222 shell lines. Tiny per-line costs (prompt round-trip + stderr grace) dominated at scale.
- What we do now: Measure new tools at realistic sizes (hundreds of elements) and batch at the transport layer (F25, D-014).

### 2026-09-27 — A good field report quotes markup
- What happened: Field report 2 quoted the exact `<tspan … dy="1.35em">` markup behind the text bug; E17 confirmed and explained it in one run.
- What we do now: The field-report template asks for exact calls and responses; keep that — it turns bug hunts into single experiments.

### 2026-09-27 — Use screen terms, not geometric ones, in agent-facing options
- What happened: `label_offset` sign = "left of travel direction" put a label below a leftward line; the test expected above. If the author gets it wrong, an agent will.
- What we do now: Options speak the agent's language (above/below/left/right, top/middle/bottom), with `auto` defaults.

### 2026-09-27 — Field test 2 → 8 calls instead of 31 (E18)
- The same loop, zones, heat arrows, wrapped steps and COP chart: no helper objects, no split connectors, no hand-computed polygons, baselines or data coordinates.

### 2026-09-27 — Windows tooling traps
- `pip` on PATH belongs to Python 3.13 while `python` is 3.12 → use `uv run` for everything.
- PowerShell 5.1 `Set-Content -Encoding utf8` writes a BOM → edit source files with the editor tools, not PowerShell.
- PowerShell 5.1 splits a here-string commit message containing `"` into bogus pathspecs (and `2>$null` hid the failure) → `git commit -F <file>`, and check `git log` after committing.
