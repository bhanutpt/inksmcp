# Benchmarks

How much work an agent needs for a fixed set of reference tasks, so each phase can show a number
instead of "it got better". Script: [`experiments/e20_benchmark.py`](../experiments/e20_benchmark.py).

## Method

- Each task is the call sequence a well-informed agent would make with the tools of the day: a
  **lower bound** (no retries, no exploration, no previews beyond the ones listed). Field reports
  measure the real thing; this measures what the API makes possible.
- Measured over stdio against a warm server (shell start excluded): calls, request characters
  (tool name + JSON arguments), response text characters, preview images (tokens ≈ w·h/750), and
  wall time. **≈ tokens = (request + response chars) / 4 + image tokens.**
- The tool list the client loads once per session is measured separately.
- Each task's last preview is saved as `experiments/out/e20_<task>.png`. Check them before you
  trust a run: a task that produces the wrong picture doesn't count.
- When a tool changes a task's best call sequence, update the task in the script and add a new
  dated table below. Keep the old tables.

## Tasks

| Task | What | Stands for |
|---|---|---|
| flowchart | 6 steps with a decision, a side branch with a labelled arrow, a loop back, page fitted | diagrams (E06–E12) |
| graph_paper | A4 log-log 3 × 5 cycles with labels, 1 zoomed check, PDF export | field test 1 |
| bar_chart | 5 horizontal bars, category names, value labels inside/outside | field test 3 chart |
| icon | 48 px cloud-upload icon: boolean union + difference, 256 px PNG | icons / path ops |
| timeline | 4 alternating cards on a spine: badge, year, title, wrapped text, card height from line count | field test 3 timeline |

## Results

### 2026-09-27 — end of Phase 2 (21 tools)

Tool list: **21 tools, 25,248 chars ≈ 6,300 tokens** per session.

| Task | Calls | Errors | Request chars | Response chars | Image tokens | ≈ Tokens | Seconds |
|---|---|---|---|---|---|---|---|
| flowchart | 8 | 0 | 2,956 | 1,680 | 777 | 1,936 | 2.2 |
| graph_paper | 5 | 0 | 525 | 346 | 1,287 | 1,505 | 0.7 |
| bar_chart | 5 | 0 | 2,227 | 855 | 384 | 1,154 | 1.2 |
| icon | 6 | 0 | 961 | 355 | 87 | 416 | 0.5 |
| timeline | 4 | 0 | 3,002 | 299 | 651 | 1,476 | 0.2 |

What this run shows:
- **The tool list costs more than any single task.** `connect` alone is 4,247 chars, mostly the
  JSON schema of 20 optional `Connection` fields (every `X | None` becomes an `anyOf` with null).
  Next come `grid` (2,696), `align`, `layout` and `plot` (~1,900 each). Trimming schemas and
  descriptions saves tokens in every session.
- **Previews are the biggest cost for simple tasks.** On graph paper, two previews are 85 % of the
  tokens.
- **The timeline has the most request text for its size**: 3,000 chars for 4 entries, because
  every coordinate is computed and sent. A `repeat`/template tool should cut this, and the table
  will show by how much.
- The flowchart only works in this order: centre the labels first, then `layout` the
  `[shape, label]` pairs. With the labels still at (0, 0), the pairs measured too wide and the
  column came out skewed (see lessons learned).
