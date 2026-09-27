# Field reports

Reports written by agents (or people) who **used** inksmcp for a real task in a separate session —
not by the session that builds it. They are the "real usage" step of the method in
[../README.md](../README.md): what the agent still had to compute, work around or guess becomes
the next feature, finding or fix.

File name: `YYYY-MM-DD-<task>.md`. Template:

```
# <task>
- Date / client / model:
- Result files:
- Tool calls (approx.) and time:

## What worked well
## What was awkward (agent had to compute, retry, or work around)
## Missing tools or options
## Bugs / surprising behaviour (with the exact call and response)
## Suggestions
```

| Date | Task | Outcome | Follow-ups |
|---|---|---|---|
| 2026-09-27 | [A4 log-log graph paper, 3 x 5 cycles](2026-09-27-log-graph-a4.md) | Done in 14 tool calls; all coordinates computed outside the tools | ✅ All addressed 2026-09-27 (E15, E16): multi-id export fixed, `region` + zoom-by-ids in `render_preview`, `grid` tool, `defaults`, `vertical_anchor`. Same sheet now takes 6 calls, no external script. |
| 2026-09-27 | [A4 landscape poster: How a Heat Pump Works](2026-09-27-heat-pump-poster.md) | Done in 31 tool calls; `grid` handled the chart axes; multi-line text renders with a doubled first gap; loop needed waypoint helpers; data points and block arrows computed by hand | ✅ Addressed 2026-09-27 (E17, E18): multi-line text fixed, arrow stub fixed, `plot` + axis titles, connector `from_side`/`to_side`/`via`, label position/side/offset/font/halo, `marker_start`/`marker_end`, `arrow` element, text `width` wrapping, `move_to_layer` position. Hard parts of the poster now 8 calls (was 31). Open: hanging indents / lists in wrapped text. |
| 2026-09-27 | [A3 portrait infographic: History of Flight 1903–1969](2026-09-27-flight-infographic.md) | Done in 26 tool calls; text wrapping + `wrapped_lines`, icon groups with transforms, `layout`/`align` baselines worked well; timeline positions and card heights computed by hand; bar chart faked with thick `plot` lines; plot labels have a hidden white halo | Open: `repeat`/template stamping (with alternate mirroring), auto-sized text box, bar series + category axis in `plot`, per-axis gridlines, plot label anchor/halo docs + series-based ids, bleed/crop marks on export. |
