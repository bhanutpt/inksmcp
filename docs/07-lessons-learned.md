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

### 2026-09-27 — Windows tooling traps
- `pip` on PATH belongs to Python 3.13 while `python` is 3.12 → use `uv run` for everything.
- PowerShell 5.1 `Set-Content -Encoding utf8` writes a BOM → edit source files with the editor tools, not PowerShell.
