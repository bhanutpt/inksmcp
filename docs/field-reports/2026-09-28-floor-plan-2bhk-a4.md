# A4 architectural drawing: 2 BHK apartment, furniture layout plan (monochrome)
- Date / client / model: 2026-09-28 / Claude Code (desktop app, Code tab) / Claude Opus 5.5.
  Written by the session that also works on inksmcp (same caveat as reports 4–6).
- Result files: `out/floor-plan-2bhk-a4.svg`, `out/floor-plan-2bhk-a4.pdf` (text to path, 194 kB),
  `out/floor-plan-2bhk-a4.png` (300 dpi, 501 kB)
- Tool calls (approx.) and time: 16 inkscape tool calls (1 document_create, 4 add_elements,
  3 path_operation, 2 repeat, 1 update_elements, 2 render_preview, 1 document_save, 2 export). 3 editing
  calls used `preview: true`. Plus a 150-line Python script that generated the architectural
  geometry (1 Write, 2 shell runs [the first failed on heredoc quoting], 2 file reads to copy the
  JSON into the calls). About 30 minutes. No tool errors.

Task prompt (written first): an A4 landscape, monochrome, professional furniture layout plan of a
typical Indian 2 BHK flat (~11.6 × 9.0 m). Master bedroom + attached toilet, bedroom 2, common toilet,
wash area, pooja room, living, dining, kitchen + utility balcony, living balcony. Solid poché walls
(230 / 115 mm), door swings, a sliding door, window symbols and an entry arrow. Suggested furniture
and fittings. Room names with clear sizes in ft-in; chain + overall dimensions in mm. Sheet border,
title block with north arrow, area statement, openings schedule, notes, scale bar (1:75), drawing number.

Result: every item in the prompt is on the sheet. Plan at 1:75 in a group scaled from metres; 20 wall
rects unioned into one poché with 16 openings cut out; 7 hinged doors, a 2-panel sliding door,
7 windows/ventilators; ~70 furniture/fixture outlines; 12 room labels with sizes; 2 dimension chains
+ 2 overall dimensions; an area statement (103.4 m² / 1113 ft² carpet, including balcony and utility).

## What worked well
- **A scaled group gives real-world units.** `add_elements` with a group
  `transform: "translate(34.5,48.7) scale(13.33333)"` (1 m = 13.333 mm = 1:75) and `parent: "plan"`
  on everything else. All geometry, stroke widths (0.012 m ≈ 0.16 mm on paper) and text sizes
  (0.2 m ≈ 2.7 mm) are in metres. Rotated dimension text (`transform: "rotate(-90 x y)"`) also works
  inside the group.
- **Poché walls from path operations in 3 calls**: `union` of 20 wall rects → one shape; `combine`
  of 16 opening rects; `difference`. That gave clean joins at every T and corner, and real gaps for
  doors and windows.
- **Big batches without trouble**: 126 elements in one `add_elements` (with `defaults` for the thin
  furniture style), 37 in another. No crash.
- **`repeat` for tables and scale bars**: the 12-row area statement (3 columns per row) and the
  5-segment scale bar (alternating fill via `"{f}"`) were one call each.
- Text `width` wrapping for the notes; the title-block dividers are one multi-segment path.
- The rendering is print quality: at a 1100 px zoom of a 85 × 72 mm region, wall joins, door arcs,
  dashed shower outlines and window glazing lines are all clean.

## What was awkward (agent had to compute, retry, or work around)
- **The whole architectural vocabulary had to be scripted** (~150 lines):
  - walls from centrelines into rects, with the right end extension (half the thickness of the wall it
    meets, or joints show notches or overlaps);
  - openings as rects at an offset along a wall;
  - doors: hinge on the wall face, leaf + quarter arc, with the SVG sweep flag worked out from the
    leaf/closing directions;
  - windows: frame + two glazing lines, set for each wall orientation;
  - dimension chains: line, 45° ticks, extension lines with a gap from the building, centred values,
    rotated text for vertical chains;
  - clear room sizes (centre-line size minus half-wall thicknesses) → ft-in, and areas for the statement.
- **Data went through the conversation twice**: the script's JSON (20 k characters for the detail batch)
  was read back and pasted into `add_elements`. There's no way to pass a spec file to a tool.
- **Title block rows were stacked by hand** (divider y = 31 / 58 / 125.5 / 158 / 180 / 192.5; text
  baselines relative to them). The area statement columns (x = 209 / 263 / 283, right-aligned
  numbers) and the TOTAL row with its rule were placed by hand too.
- **Label vs furniture collision**: "BEDROOM 2" overlapped the wardrobe and the bed edge. Found in the
  full-page preview and fixed with one update. That's the fourth report in a row where overlaps are
  found by eye.
- **Line weights are tied to the drawing scale**: stroke widths are in metres inside the group, so
  printing at another scale would change the pen weights. A professional drawing wants paper-space
  pens (e.g. SVG `vector-effect: non-scaling-stroke`, or a `stroke_width` in paper units).
- The scale bar needs n+1 labels for n segments, so there was an extra element for "5 m".

## Missing tools or options
- **Dimension element** (common for any technical drawing): `{"type": "dimension", "points": [[x, y], …],
  "offset": -1.75, "orientation": "h|v|aligned", "ticks": "arch|arrow", "text": "auto|…", "unit_scale": 1000}`,
  with extension lines from the measured points and a gap. Chains and overall dimensions as one element each.
- **Walls and openings** (architecture-specific): `wall` from a centreline polyline + thickness with
  automatic joins, and `door`/`window` elements placed on a wall by offset (hinge side, swing side).
- **Paper-space line weights** for scaled groups (non-scaling stroke), or a document-level drawing scale.
- **Table element**: rows × columns with column x/alignments, header, rules, a total row. Would cover
  area statements, schedules, legends and BOMs.
- **Specs from a file**: `add_elements`/`repeat` taking a JSON path, so generated data doesn't pass
  through the model. The periodic table (report 6) would have benefited too.
- **Overlap warnings** (again) and **section stacking** (again: title block).

## Bugs / surprising behaviour (with the exact call and response)
1. **`path_operation` result id: `combine` keeps the top object's id, but the description says the bottom's.**
   `union` of `w0…w19` → `{"removed": ["w1","w10",…,"w9"], "created": []}`, so `w0` (bottom) survived,
   as documented. `combine` of `o0…o15` → `{"removed": ["o0","o1","o10",…,"o9"], "created": []}`, so
   **`o15` (top) survived**. That contradicts "The result keeps the bottom object's id and style". The
   response doesn't name the survivor either; I had to work it out from the `removed` list before
   calling `difference ["w0","o15"]`. Expected: consistent (bottom) id, plus a `result` id in the response.
   Per D-021, fix now (small).

## Suggestions
- Most useful for technical drawings: **a dimension element**. It was the most error-prone part of
  the script and applies to plans, mechanical sketches and annotated diagrams.
- **Specs from a file** is cheap and cuts token use for every data-heavy drawing.
- Fix the `path_operation` id inconsistency and return the result id.

## Common or task-specific? (input for the round-2 synthesis)
| Need | Seen before? | Guess |
|---|---|---|
| Dimension element (chains, ticks, extension lines) | Report 1 (graph paper: axes by hand) | Common for technical drawings |
| Walls + door/window openings | New | Specific (architecture); could be a template/recipe rather than core |
| Paper-space line weights in scaled groups | New | Common for anything drawn to scale (plans, maps, mechanical) |
| Table element | Report 6 (legend grid), report 4 (guide box) | Common: schedules, statements, legends |
| Specs from a JSON file | Report 6 (118 rows pasted) | Common for data-heavy tasks |
| Overlap warnings | Reports 4, 5, 6 | Common (4 of 4 in round 2) |
| Section stacking (title blocks, poster sections) | Reports 4, 6 | Common |
| `path_operation` result id | New | Bug: fix now |
