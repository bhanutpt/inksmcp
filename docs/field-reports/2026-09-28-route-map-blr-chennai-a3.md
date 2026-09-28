# A3 route map from OpenStreetMap data: Bengaluru → Chennai via Chittoor District
- Date / client / model: 2026-09-28 / Claude Code (desktop app, Code tab) / Claude Opus 5.5.
  Written by the session that also works on inksmcp (same caveat as reports 4–7).
- Result files: `out/route-map-blr-chennai-a3.svg`, `.pdf` (text to path, 459 kB), `.png` (300 dpi, 1.9 MB);
  intermediate `out/map-base-geometry.svg` (script-generated geometry, 56 kB)
- Tool calls (approx.) and time: 18 inkscape tool calls (1 document_create [abandoned, see below],
  1 document_open, 3 add_elements, 6 repeat, 1 run_actions, 3 render_preview, 1 document_save,
  2 export). 2 editing calls used `preview: true`. Outside the MCP: 4 Python scripts (fetch, project/simplify,
  element specs, SVG writer), ~9 runs (one Overpass HTTP 429 and retry; one simplification bug in my own code),
  1 truncated file read. About 40 minutes.

Task prompt: a map of the road from Bengaluru to Chennai through Chittoor district (Andhra
Pradesh), from real OpenStreetMap data. It shows key towns, cities, connecting roads and landmarks.
The route is emphasised; everything else is high-level context.

Data (fetched 2026-09-28): the OSRM public router (driving, waypoint in Chittoor) → 348.2 km, 4 h 26 min,
4,624 points, with the step refs NE7 / NH75 / NH42 / NH69 / NH40 / NH48. Overpass (bbox 12.35–13.95 N,
77.25–80.45 E): 132 city/town nodes; 7,805 motorway/trunk ways (74,798 points); 3 state relations; the
Chittoor district relation (86 outer ways); 55 coastline ways; 478 named lakes; landmarks (airports with
IATA codes, temples, fort, hills).

Result: A3 landscape, equirectangular projection at 13.15° N, 1:875 000. Context layers: land, sea,
lakes over 4 mm², graticule every 0.5° with edge labels, state boundaries (dash-dot), Chittoor district
tint + dashed edge, motorway/trunk network in muted browns. The route is red with a white casing
and 6 highway shields at segment midpoints (green NE-7, navy NH). There are 9 route towns with the distance
from Bengaluru, 27 context towns, and 11 landmarks (3 airports, 5 temples, a fort, 2 hills). Around the map:
state/sea/lake/district names, a legend (13 items), a route-section table (6 rows + total), a scale bar,
a north arrow and OSM/OSRM attribution.

## What worked well
- **`repeat` as a cartographic symboliser.** Placeholders in *style* fields (`font_size`, `font_weight`,
  `text_anchor`, `fill`, `r`, `stroke_width`, even the symbol glyph `"{g}"`) made each layer one call.
  27 context towns, 11 landmarks (4 symbol types from one template), 9 route towns (dot + label + km
  label, each placed separately), 6 shields.
- **Label halos** via `stroke` + `style: {"paint-order": "stroke"}` on texts. They read cleanly over roads and
  district edges at 1100 px zooms. `letter-spacing` in `style` worked for the state names.
- **Shields = `fit_to` rect + text with `vertical_anchor: middle`** inside `repeat` (`fitted` returned
  every box). Same trick for the route-section table's badges.
- **`document_open` of a script-generated SVG** kept its layer and group structure. The tools then worked on it
  as on any document (clip, add, repeat, export).
- **Clipping via `run_actions object-set-clip`** (the recipe from report 5) cut roads and borders at the map frame.
- **Tables and scale bars with `repeat`** again (third report): 6-row route-section table, 5-segment
  scale bar.
- Zoom previews confirmed print quality. Predicting and resolving label conflicts before drawing
  (Chittoor/Kanipakam, Vellore/Ranipet, Kanchipuram/Kailasanathar, Tirupati/TIR, Poonamallee/MAA) left
  only one minor overlap (Vellore Fort symbol over the Vellore dot, which is where the fort really is).

## What was awkward (agent had to compute, retry, or work around)
- **The geometry could not go through the tools at a reasonable cost.** After projection and
  Douglas-Peucker simplification the base layers were 51 kB of path data (≈50 k tokens). Reading it back
  was truncated at 25 k tokens, and writing it as tool arguments would have cost more than the whole rest
  of the task. Workaround: the script wrote the geometry layers into an SVG, and `document_open` made it
  the current document. That meant the `document_create`d doc7 was abandoned. There is no way to *add*
  a file's content (SVG fragment or spec JSON) to an existing document.
- **All GIS work was scripted**: fetching (with a 429 backoff), projection, simplification (my first
  version collapsed closed rings: a bug in my code, the kind of thing a tool would get right once),
  multipolygon ring assembly for the district and lakes, a sea polygon from the coastline, area filtering,
  distance-along-route for the km labels, shield positions at segment midpoints, "town on route" by distance.
- **Label placement is by hand**: every label position/anchor was chosen by reasoning over coordinates
  (≈50 labels). The tools don't warn about collisions (fifth report in a row).
- The scale bar needs an extra element for the last label (as in report 7). The legend was 29 hand-placed
  elements (symbol + text pairs of different symbol types, so `repeat` didn't fit).
- A repeated template can't vary the element *type* per row (circle vs square for major cities; glyphs
  worked around this for landmarks).

## Missing tools or options
- **Import into the current document**: `import(path, layer=…, at=…)` for an SVG file (as a group),
  and/or `add_elements(specs_path=…)` / `repeat(rows_path=…)`. This is the most important finding here: it
  decides whether data-heavy drawings are possible through the MCP at all. (Also needed for the comic
  direction: character/asset libraries.)
- **Geo layer** (cartography-specific; maybe an optional module): GeoJSON/OSM JSON → projected,
  simplified, clipped paths (`project: equirectangular|mercator`, `bbox`, `frame`, `tolerance_mm`), with
  ring assembly and area filters. It would remove ~200 lines of script.
- **Text halo as a first-class option** on any text (`halo: "#ffffff"`, `halo_width`), as `plot` and
  `connect` already have for their labels.
- **`clip` as an element/group key** (second report asking for it).
- **Label collision check**: report overlapping text bboxes (maybe with a suggested free position among
  N/NE/E/…). For maps this is the main remaining manual work.
- **Scale bar / legend helpers**: a scale bar from the drawing scale (reports 7, 8); legend rows that
  pair a symbol spec with a label.
- **Row-varying element type in `repeat`** (e.g. `"type": "{shape}"`).

## Bugs / surprising behaviour (with the exact call and response)
None in inksmcp. (Outside the MCP: Overpass returned HTTP 429 on the third query; solved with backoff.)

## Suggestions
- Build **import / specs-from-file** first: it's cheap and decides whether data-heavy work fits.
- Consider a **geo layer** as an optional, cartography-specific tool once import exists: the projection and
  simplification code from this test is a ready starting point.
- **Text halos and overlap warnings** would make `repeat`-based labelling close to production quality
  without zoom-and-fix loops.

## Common or task-specific? (input for the round-2 synthesis)
| Need | Seen before? | Guess |
|---|---|---|
| Import SVG / specs / rows from a file into the current doc | Report 7 (20 k pasted), report 6 (118 rows), comic memory | Common: decides feasibility of data-heavy tasks |
| Overlap / label collision warnings | Reports 4–7 | Common (5 of 5 in round 2) |
| `clip` key | Report 5 | Common (panels, map frames, image crops) |
| Text halo option | Plot/connect labels already have it | Common for maps, charts, labels over art |
| Table element | Reports 6, 7 | Common (3 reports) |
| Scale bar helper | Report 7 | Common for anything to scale |
| Row-varying element type in `repeat` | New | Minor, common |
| Geo layer (projection, simplification, rings) | New | Specific (cartography): optional module |
