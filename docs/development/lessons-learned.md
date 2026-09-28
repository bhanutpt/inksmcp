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
- What we do now: Those become the next features (layout, align-to, connectors). See `features.md`.

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

### 2026-09-27 — A dict literal is not a switch
- What happened: `{1: pad * 4, 2: [pad[0], pad[1], ...], 4: pad}[len(pad)]` evaluates every branch, so a one-number padding raised IndexError, which MCP reported only as "Error executing tool".
- What we do now: use if/elif for normalising. When a tool error has no message, the cause is a non-DocumentError exception: read the traceback in the test output.

### 2026-09-27 — Place labels before you lay out their groups
- What happened: in the E20 flowchart, `layout` of `[shape, label]` pairs ran while the labels were still at (0, 0). Each pair measured too wide and the column was skewed; straight connectors leaned.
- What we do now: centre the labels (`align`) first, then `layout`. Backlog: `layout` could warn when the members of an item don't overlap.

### 2026-09-27 — The tool list is the biggest fixed cost
- What happened: the benchmark put the tool list at ≈ 6.3k tokens per session, more than any reference task (0.4k–1.9k). Optional pydantic fields (`X | None`) each add an `anyOf` with null to the schema.
- What we do now: measure schema size alongside calls (`benchmarks.md`); trimming is on the Phase 4 list.

### 2026-09-27 — Hidden styling is a trap: say it in the tool description
- What happened: `plot` labels carried a white halo stroke the description never mentioned; the field-test agent recoloured a label white and got an unreadable blob, then needed an extra call.
- What we do now: Any styling a tool adds on its own (halos, bold, anchoring) is named in the tool description and has an option to turn it off.

### 2026-09-28 — A check must know the workflow it runs in
- What happened: the first version of the overlap warnings flagged every pair in the pile of elements that the E20 flowchart drops at the origin before arranging them. That is the workflow our own server instructions recommend, and it produced 12+ warnings per call. The same run showed value labels inside thick bars reported as "crossed".
- What we do now: run the reference benchmark with `E20_SHOW_WARNINGS=1` whenever a check changes, and treat each noisy line as a false positive to design out (stacks are reported once; labels within a thick stroke are exempt).

### 2026-09-28 — Test on files you didn't write
- What happened: ten field tests drew new documents, so every file the tools saw had our own page geometry, styles in `style` and ids everywhere. The first test on Inkscape's sample files found 12 problems in an hour, including a coordinate bug (F35) that affects any file whose viewBox doesn't match its page.
- What we do now: every release gets a field test on foreign files (samples shipped with Inkscape, web exports), run by a fresh agent that sees only the tool descriptions.

### 2026-09-28 — lxml proxies have no stable `id()`
- What happened: `find` collected Python `id()`s of elements inside defs to skip them; lxml creates proxy objects on demand, so ids were reused by unrelated elements and matches vanished at random.
- What we do now: test membership with the tree (ancestors), or keep the element objects themselves alive in the set.

### 2026-09-28 — A warning is only as good as its worst false positive
- What happened: the overlap check shipped with tests built from its own design cases (labels, roads, boxes). The first real page with a patterned background produced 15 warnings, all for texts on opaque balloons, enough to fill the 12-line cap and hide a real one.
- What we do now: replay every finished page in `out/` through a check before trusting it (E29 does this for overlaps); a new check needs a "real pages, zero noise" run, not just the cases it was designed for.

### 2026-09-28 — A partial write is worse than a failure; the transcript knows when it broke
- What happened: an intermittent shell crash left `add_elements` half-applied (elements written, not wrapped or fitted) behind an error that implied nothing happened. A 200-iteration stress loop could not reproduce it; the session transcript's timestamps showed it was the first call after ~28 idle minutes, and an idle experiment reproduced it once in 5 runs (cause still unknown).
- What we do now: every tool snapshots the document and restores it on any failure (D-022), and a dead shell is retried once. For intermittent failures, read the transcript timeline before writing stress loops, and make the error carry diagnostics (exit code, command) for next time.

### 2026-09-28 — Python `write_text` on Windows writes CRLF
- What happened: patching sources with `Path.write_text` turned LF files into CRLF (git warned on diff).
- What we do now: write with `open(p, "w", newline="\n")`, or use the editor tools. A bulk CRLF → LF fixer
  must skip binary files: one pass over `git ls-files -m -o` rewrote `\r\n` byte pairs inside six PNGs
  (2026-09-28; regenerated and CRC-checked before the commit).

### 2026-09-27 — Windows tooling traps
- `pip` on PATH belongs to Python 3.13 while `python` is 3.12 → use `uv run` for everything.
- PowerShell 5.1 `Set-Content -Encoding utf8` writes a BOM → edit source files with the editor tools, not PowerShell.
- `uv run` re-syncs the project after a version bump and fails with os error 32 while the MCP server from `.mcp.json` is running (`.venv/Scripts/inksmcp.exe` is locked); piping into `tail` hid the failure. Use `uv run --no-sync` while a session holds the server, and never trust a test summary line you didn't see.
- PowerShell 5.1 splits a here-string commit message containing `"` into bogus pathspecs (and `2>$null` hid the failure) → `git commit -F <file>`, and check `git log` after committing.
