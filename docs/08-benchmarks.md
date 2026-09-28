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

### 2026-09-27 — `repeat` (22 tools)

Tool list: **22 tools, 27,434 chars ≈ 6,860 tokens** (`repeat` adds ≈ 2.2k chars).
Only the timeline changed. It is now one `repeat` with `mirror` instead of computed positions.

| Task | Calls | Errors | Request chars | Response chars | Image tokens | ≈ Tokens | Seconds |
|---|---|---|---|---|---|---|---|
| timeline | 5 (was 4) | 0 | 1,887 (was 3,002) | 594 (was 299) | 651 | 1,271 (was 1,476) | 0.4 |

- **37 % less request text at 4 rows, and nothing is computed by hand.** The template is a fixed
  cost; each extra row adds only its data (≈ 100 chars) instead of 5 positioned elements
  (≈ 700 chars). Field report 3's 8 rows would be about 2.3k chars instead of about 6k.
- There is one extra call because the spine is no longer in the same batch as the cards.
- The response is larger: ids come back for 7 template names × 4 rows.

### 2026-09-27 — rect `fit_to` (22 tools)

Tool list: **27,742 chars ≈ 6,940 tokens**. The timeline's card boxes now `fit_to` their texts
inside the `repeat` template, so the follow-up height update is gone.

| Task | Calls | Errors | Request chars | Response chars | Image tokens | ≈ Tokens | Seconds |
|---|---|---|---|---|---|---|---|
| timeline | 4 (Phase 2: 4) | 0 | 1,749 (Phase 2: 3,002) | 703 | 651 | 1,264 | 0.45 |

- Compared with Phase 2, the timeline sends **42 % less request text** in the same number of
  calls, and the agent computes no positions and no heights.
- The response grows by the `fitted` boxes (≈ 25 chars per card).

### 2026-09-28 — Round-2 step 0 (22 tools)

Tool list: **29,726 chars ≈ 7,430 tokens** (+2.0k chars: `clip`/`halo` help, connector gaps, the `repeat`
component pattern). Task numbers unchanged; the benchmark is re-run after step 2 (D-024).

### 2026-09-28 — Round-2 step 1: files in (23 tools)

Tool list: **32,253 chars ≈ 8,060 tokens** (+2.5k: `import_file`, `image`, data paths).
E26 (a stand-in for field report 8's map: 51 kB of road geometry from a script, 40 towns in a CSV, a clip to the
frame, a photo inset): **7 calls, 1,095 request chars, 737 response chars**. Before step 1 the geometry alone
was ≈ 50k tokens and didn't fit through the tools.
