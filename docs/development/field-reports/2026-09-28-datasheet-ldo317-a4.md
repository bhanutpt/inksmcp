# A4 datasheet page: LDO-317 (synthetic) typical characteristics, 4 plots
- Date / client / model: 2026-09-28 / Claude Code (desktop app, Code tab) / Claude Opus 5.5.
  Written by the session that also works on inksmcp (same caveat as reports 4–9). While diagnosing
  bug 1, the agent read `src/inksmcp/grids.py` (a real field tester could not).
- Result files: `out/datasheet-ldo317-a4.svg`, `.pdf` (text to path, 255 kB), `.png` (300 dpi, 718 kB)
- Tool calls (approx.) and time: ~41 inkscape tool calls (1 document_create, 7 grid [1 wrong axis, 2 redone
  for log labels], 6 plot, 4 delete_elements, 5 inspect, 5 repeat, 3 add_elements, 2 update_elements, 1 align,
  1 layout, 1 z_order, 2 render_preview, 1 document_save, 2 export). 1 shell call generated the synthetic curves.
  About 35 minutes. The call count is double the other round-2 tasks; the redos come from bugs 1–2 below.

Task prompt: A4 portrait "Typical Characteristics" page for a fictional LM317-style regulator with
synthetic data. 4 plots in a 2 × 2 grid mixing axis types: dropout vs current (linear, 3 temperatures),
reference voltage vs temperature (linear, fine decimals), ripple rejection vs frequency (log x), output
impedance vs frequency (log/log). Curve labels, a test-condition box and a caption for each figure,
a header band, section title, key-parameter table and footer. The goal was to test the layout engine,
not LM317 accuracy.

Result: every item in the prompt is on the page. Four 72 × 60 mm plots, with frames aligned in columns and
rows after one `layout` + a manual correction. 8 series, a 3-entry legend (Figure 1), on-curve labels
(Figures 3–4), 4 condition boxes, 4 captions, a 6-row parameter table, and page header/footer.

## What worked well
- **`plot` on linear and log axes**: data values in, correct placement out, including `start: 10` /
  `start: 0.001` on log axes. Series ids, a per-figure "FigN data" layer created automatically,
  `point_labels` with halo, colour and anchor.
- **`grid` linear axes** (after exact spacings): ticks, labels, axis titles and rotated y title in one call.
  `bold_major: false` gave datasheet-style labels.
- **`layout` grid of figure blocks**: 4 blocks of 4–5 layers each, `columns: 2`, `gap: [10, 12]`,
  `to: page`, `horizontal: center`, `vertical: top`, `margin: 42`. Rows came out aligned exactly.
- **`repeat` for decade labels, the parameter table (6 rows × 7 elements) and the legend**; `fit_to` for the
  condition boxes and the legend box; `z_order back` put the legend box behind its entries.
- **`align` on rotated text** (`horizontal: right`, `margin`) moved the rotated y-axis title correctly.

## What was awkward (agent had to compute, retry, or work around)
- **A figure is spread over 4–5 layers** ("Fig1 minor/major/labels/data", …), not one group. Deleting a figure
  or moving it as a block needs its layer ids from `inspect`. The `layout` call listed 17 layer ids.
- **Layout aligns bounding boxes, but a datasheet aligns plot frames.** Tick labels of different widths
  ("1.27" vs "3", "0.001" vs "100") put the frames of Figure 3 / Figure 4 0.52 / 1.42 mm right of
  Figure 1 / Figure 2. I fixed it by setting 9 layer transforms by hand from `inspect` bboxes.
- **Log axes needed hand-made labels** (bug 2): `repeat` rows for 10 … 1M and 0.001 … 10, then moving the
  auto-placed axis titles (`update y`, `align` for the rotated one), because the grid placed them as if
  there were no tick labels.
- **On-curve labels on close, sloped curves** (Figure 1, 4 mm apart): a centred label always touches a
  neighbouring line; the halo hides the collision instead of avoiding it. I replaced them with a legend
  built from 3 tools (`repeat`, `add_elements fit_to`, `z_order`). `plot` has no legend option.
- **Adding into a transformed layer** after `layout`: I avoided adding legend elements to "Fig1 labels"
  (now translated) because it wasn't clear whether page coordinates would be offset. I used a new layer.

## Missing tools or options
- **`grid` as one group per figure** (`group: "fig1"`), with the grid, labels and plotted data inside it.
  Then one id moves, deletes or lays out a figure.
- **Layout by anchor**: per item, name the member used for alignment (`anchor: "f3-border"`), or
  `align_by: "border"` in `layout`, so plot frames line up regardless of label widths.
- **Log-axis label styles**: `labels: "decades"` (10, 100, 1k, 10k with SI prefixes), `"scientific"`
  (10ⁿ) or `"paper"` (today's 1..9), respecting `start`.
- **`plot` legend**: `legend: {"position": "top-left", "box": true}` built from series names/colours.
- **Axis title offset** (or automatic placement that accounts for labels added later).
- **Table element** (fourth report asking).
- **Label-collision check** for plot labels (seventh report asking for overlap warnings).

## Bugs / surprising behaviour (with the exact call and response)
1. **`grid`: major lines silently disappear when `major` isn't an exact decimal multiple of `minor`.**
   Call: `grid(rect=[30,45,70,60], x={"scale":"linear","major":11.6667,"minor":2.3333,"label_start":0,"label_step":0.25}, …)`
   → `{"lines":{"minor":54,"medium":0,"major":5},"labels":10}`. The x axis had **no major lines and only the
   label "0"**; the y axis was fine. Cause (from `grids.py`): lines are generated at multiples of the finest
   spacing and classified with `multiple(pos, major)`, whose tolerance is 1e-6 relative; 5 × 2.3333 =
   11.6665 ≠ 11.6667. No error or warning. Expected: classify by index (every round(major/minor)-th line),
   or warn "major is not a multiple of minor". Workaround: exact spacings (72 mm, major 12, minor 2.4).
   Per D-021, fix now.
2. **`grid` log labels ignore `start` and don't suit engineering plots.**
   `grid(x={"scale":"log","cycles":5,"start":10,"subdivisions":"integers"}, labels={"sides":["left","bottom"], …})`
   → labels "1 2 3 … 9" in each decade starting at "1", overlapping at 14.4 mm per decade. `plot` uses
   `start` (10 at the origin), so the labels contradict the data. This is documented behaviour ("as on
   printed log paper"), but the inconsistency with `plot` makes it a bug. Fix now: at least label the
   decades with `start × 10^k` when `start` is given.
3. (Minor) `plot` warned "point [1.5, 2.84] lies outside the grid" for points that mapped 0.0002 mm beyond the
   edge (a consequence of bug 1's rounded spacing). An edge tolerance would avoid false warnings.

## Suggestions
- Fix bugs 1–2 (small, in `grids.py`).
- For multi-chart pages, the two structural features are **figure = one group** and **layout by anchor**.
  Together they would have made this page ~20 calls.
- A `plot` legend and log label styles make datasheet/engineering charts first-class.

## Common or task-specific? (input for the round-2 synthesis)
| Need | Seen before? | Guess |
|---|---|---|
| Layout aligned by an anchor member (frames, not bboxes) | New | Common: dashboards, forms, multi-chart pages |
| Grid/figure as one group | New | Common for charts |
| Overlap/label-collision warnings | Reports 4–9 | Common (7 of 7) |
| Table element | Reports 6, 7, 8 | Common (4 reports) |
| Plot legend | Report 2 (legend by hand) | Common for charts |
| Log label styles (decades, SI prefixes) | Report 1 (log paper) | Engineering charts: common within the domain |
| Grid spacing robustness, log labels vs `start` | New | Bugs: fix now |
