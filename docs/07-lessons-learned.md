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

### 2026-09-27 — Windows tooling traps
- `pip` on PATH belongs to Python 3.13 while `python` is 3.12 → use `uv run` for everything.
- PowerShell 5.1 `Set-Content -Encoding utf8` writes a BOM → edit source files with the editor tools, not PowerShell.
