# Editing SVG files someone else made (re-run): tiger.svgz, NPS symbol legend, car.svgz, flowsample
- Date / client / model: 2026-09-28 / Claude Code subagent / Claude Opus 5.5 (claude-opus-5-5).
  Field tester only: I did not read the server's source, docs or tests. I learned the tools from
  their descriptions and responses. Server **0.3.0**, Inkscape 1.4.4.
- Result files (all in `out/edit-test-2/`):
  - Job 1: `tiger-edited.svgz` (30 kB, gzip header checked), `tiger-edited.pdf` (41 kB),
    `tiger-head.png` (600 x 619 px).
  - Job 2: `park-legend.svg` (8 kB, 6 symbols in defs), `park-legend.png` (150 dpi, 620 x 874 px).
  - Job 3: `car-green.svg` (493 kB, plain SVG), `car-green.png` (900 x 600 px). flowsample: inspected only.
- Tool calls (approx.) and time: 62 inkscape calls, about 30 minutes. 2 general calls (`inkscape_info`,
  1 ToolSearch).
  - Job 1: 12 calls, 0 errors, 0 retries. Nothing computed by hand.
  - Job 2: 12 calls, 0 errors, 1 redo (3 calls: wrong icon size, see bug N1). Hand maths: column
    pitch 52.5 and icon x 15.25 for a 105 mm page, scale 22/72 = 0.305556.
  - Job 3 (car): 30 calls, 0 errors, but 1 destructive surprise (`run_actions`, bug N3) that cost a
    reopen, and about 12 calls of trial and error around gradients. Hand maths: the vent region
    (later dropped). flowsample: 6 calls, 1 expected error.
  - Plus 1 test call for old bug 9 (1 expected error).
- Fallbacks used: **no raw SVG read.** **1 shell call** (PowerShell) at the end, to get file sizes,
  the PNG pixel sizes and the first two bytes of the `.svgz` (no tool reports these).
  **1 `run_actions`** (`org.inkscape.color.desaturate`), because no tool can recolour gradient stops.
  I also opened `tiger-head.png` with Read to look at the export.

## The jobs and what came out
- **Job 1. Finished.** `.svgz` opened directly. The open response explained the page fix
  (`width="100%"` read as the viewBox width, content translated, root `fill`/`stroke` moved down).
  `inspect find {"fill": "rgb(153,204,50)"}` found three green eye paths in one call. The two darker
  tops (`path119`, `path162`, `rgb(102,153,0)`) I found in a big `id_prefix` listing; I could have
  searched that colour directly if I had known it. Eyes are now blue. Dark "TIGER" banner placed 16 px
  below `g3` with `place`, text centred with `align`. `page_fit` margin 20 gave 584.568 x 687.499 px
  and the preview was 680 x 800 (same ratio): **no white band**. Saved as gzip `.svgz`, PDF and a
  600 px head crop (`export ids ["g3"]`, which leaves the banner out).
- **Job 2. Finished.** `inspect find {"type": "symbol"}` listed all 103 symbols with titles, so I could
  pick the six `_Inv` (framed) ones by name. One `repeat` call with
  `href: "...MapSymbolsNPS.svg#{sym}_Inv"` and a `place`d label drew the 2 x 3 grid. Title and rule in
  one `add_elements`. The saved file has only the 6 used symbols (8 kB).
- **Job 3. Mostly finished.** The body base colour was easy: `inspect layer "main_color"` showed one
  flat `#ffbe00` path (`path2177`) and 60 gradient fills. Changing that path gave an olive, patchy car,
  because the shading paths above it use yellow gradients. **No tool shows or changes gradient stop
  colours.** I got a good dark green body with two blend-mode overlay rects (`mix-blend-mode:color`
  then `multiply`) clipped to `path2177`, and moved the window paths and steering wheel above them
  with `z_order`. Still yellow: the side vents, the sill strip and the reflection in the headlamp
  covers (they sit in other layers, also gradients). Caption added under the car with `place`.
- **flowsample.svg.** `document_open` now lists it: one `flowRoot908`, type `flowtext`, fill `#000000`,
  text (first 160 characters, then "..."), a note "SVG 1.2 flowed text: move, align, delete and z-order
  work; its text can't be edited.", bbox `[23.71, 471.22, 552.54, 193.61]`. Page 793.7 x 1122.5 **px**.
  It does not tell me there are 2 flow regions, an exclusion, 3 paragraphs in two scripts (English,
  Arabic), or the red and blue coloured words the preview shows.

## What worked well
- **`.svgz` in and out.** Open and save both work; the saved file really is gzip (`1F 8B`).
- **The open notes are clear and honest.** "Page normalised, rendering unchanged: ...", "The root set
  fill:none; stroke:rgb(0,0,0) for everything: moved onto its top-level elements, so new elements don't
  inherit it.", "599 elements had no id and were given one ...; saving writes them to the file".
  The tiger banner had no stray black stroke this time (bbox exactly 400 x 70).
- **`inspect find` by colour** matches `rgb(...)` presentation attributes. One call found the eyes.
- **Symbols by name.** `find {"type": "symbol"}` with titles, then `use` with `library.svg#id` inside
  `repeat`. The legend body took one call once I knew the icon size.
- **Def pruning.** `delete_elements` answered `"defs_removed":6` and the saved legend holds only what it
  uses.
- **`place` against foreign groups and layers** (`g3`, `layer6`) and `placed` now returns a real
  `[x, y, w, h]` bbox that agrees with `align`.
- **`clip` with an element id** plus a CSS blend mode in `style` let me recolour a gradient-shaded
  body without touching the gradients. `z_order above/below target` reported exact positions.
- `update_elements` on `flowRoot` still refuses, but with a clear message and nothing changed.

## What was awkward (agent had to compute, retry, or work around)
- **Recolouring a gradient-shaded drawing.** "Find out what colours it uses" has no answer when most
  fills are `url(#linearGradient3111)`. I rendered paths with `only_ids` to see which were yellow
  (4 previews), tried `find {"type": "stop"}` and `find {"type": "linearGradient"}` (both `count: 0`),
  then fell back to overlays. The overlay trick needed 2 rects, 3 `z_order` calls and guessing which
  paths were windows. A per-region tint (vents) left a visible rectangle, so I removed it.
- **Symbol size.** Nothing told me the `_Inv` symbols are 72 x 72 with no viewBox. My `width`/`height`
  22 were ignored silently (bug N1). I redid the `repeat` with a group `scale(0.305556)` that I
  computed.
- **Finding the darker eye tops.** No "distinct colours" listing, so I listed 108 paths by id prefix to
  find `rgb(102,153,0)`. A palette summary would have made it one call.
- **Caption under the car.** `place below "layer3"` (the body layer) put the caption over the front
  tyre, because the wheels are in another layer. No warning. `place below "layer6"` (the ground shadow)
  worked.
- File size, PNG pixel size and "is it really gzip" needed the shell.

## Missing tools or options
- **Colour summary**: `inspect` option "list distinct fills/strokes with counts and ids", including the
  stop colours of gradients.
- **Gradient editing / recolour**: e.g. `recolor {"from": "#ffbe00", "to": "#1f4d2b", "ids" or "layer"}`
  that also rewrites gradient stops (hue shift for near colours would be even better). Or list
  gradients and stops in `inspect` and let `update_elements` change a stop.
- **Symbol size** in `find {"type": "symbol"}` (viewBox or natural bbox), and `use` width/height that
  work for symbols without a viewBox (wrap in a scale).
- `document_save` could return bytes (and say "gzip") like `export` does; `export` PNG could return
  pixel width/height.
- `inspect` of flowtext: full text (or a length), number of paragraphs/regions, colours of spans;
  `find text` should search flowtext too.
- A way to close a document (the desaturated `doc5` stays open).

## Bugs / surprising behaviour (with the exact call and response)
- **N1. `use` width/height silently ignored for a symbol without viewBox, and its size is taken as user
  units of the new document.** In a 105 x 148 mm document: `repeat` template
  `{"type": "use", "id": "icon", "href": "C:\\...\\MapSymbolsNPS.svg#{sym}_Inv", "x": 15.25, "y": 32,
  "width": 22, "height": 22}` → no warning about size; the response warned only
  `'item-2' extends beyond the page (right by 34.75 mm).` etc. `inspect find {"id_prefix": "icon-"}` →
  `"bbox":[15.25,32.0,72.0,72.0]`. The symbol is 72 px in the (px) library, so it became 72 **mm**
  (3.8 x its real size). The tool description does say "width/height scale a symbol that has a
  viewBox", but the call should warn, or scale anyway.
- **N2. No access to gradient colours.** `inspect {"find": {"type": "stop"}}` → `{"found":[],"count":0}`;
  same for `{"type": "linearGradient"}`. `find {"fill": "#ffbe00"}` finds only the one flat path.
- **N3. `run_actions` with an extension ignores `select` and changes the whole drawing.**
  `run_actions {"select": ["path2203", "path3094", ... 33 gradient paths in layer main_color],
  "actions": ["org.inkscape.color.desaturate"], "preview": true}` → `{"messages":["(org.inkscape.Inkscape:1804):
  GLib-WARNING **: ... passing a child setup function to the g_spawn functions is pointless on Windows
  and it is ignored"]}`. The preview showed the **whole car grey**, including `path2177` (which I had
  just set to green and did not select), the wheels and the background. No undo tool, so I reopened the
  file (1 call, lost 1 edit). Either extensions should get the selection, or `run_actions` should say
  that extensions act on the whole document.
- **N4. Reopening a saved file re-normalises by a rounding error.** `document_open tiger-edited.svgz`
  (just saved after `page_fit`) → `"height":687.4990866` and the note "Page normalised, rendering
  unchanged: the viewBox did not match the page's shape ... 2 top-level element(s) got
  translate(0,4.330708663e-05) in front of their transform." The server's own saved file should reopen
  without a fix, and transforms like `translate(0,4.3e-05) translate(3.0249,-81.2304)` pile up.
- **N5. No overlap warning when new text lands on existing artwork.** `add_elements` caption with
  `"place": {"below": "layer3", "gap": 14}` → `"placed":{"caption":[210.07,451.23,430.06,18.11]}`, no
  warning, but the preview shows the caption over the front tyre (layer `wheels`).
- **N6. flowtext is only partly visible.** `inspect find {"text": "SkypeOut"}` → `count: 0` although the
  preview shows "SkypeOut" in the flowed text; the outline's `text` stops at 160 characters with "...".
- Expected refusal, for the record: `update_elements [{"id": "flowRoot908", "fill": "#1b4d2e"}]` →
  `Cannot update element of type 'flowRoot' yet. (Nothing was changed.)`

## Status of the earlier report's 12 items
| # | Item | Now |
|---|---|---|
| 1 | `.svgz` cannot be opened, empty error | **Fixed.** Opened `tiger.svgz` and `car.svgz` directly; saved `.svgz` is gzip. |
| 2 | `flowRoot` invisible in the outline | **Fixed / changed.** Listed as `flowtext` with bbox, fill, text and a note. Still not editable (by design), `find text` misses it (N6). |
| 3 | Raw action `text-convert-to-regular` crashes Inkscape | Not retested (Inkscape bug; I did not want to crash it again). |
| 4 | `page_fit` gives a non-uniform page on the tiger | **Fixed.** Page normalised on open, `page_fit` result has the right ratio, no white band, no `sed`. New small issue on reopen (N4). |
| 5 | `inspect` shows no fill for presentation attributes | **Fixed.** `rgb(...)` fills shown and searchable with `find`. |
| 6 | `import_file` drops root style / scales non-uniformly | Not retested with `import_file`. The root style is now moved onto top-level elements on open, and the `use` route never needed an import. |
| 7 | Invented ids not stable | **Fixed (by the open note).** "saving writes them to the file ... import_file of the same file assigns the same ids". I did not re-import to verify. |
| 8 | Imported defs stay after delete; second import prefixes | **Fixed.** `defs_removed: 6` on delete; saved legend holds only its 6 symbols (8 kB). |
| 9 | Misleading `defaults` error | **Fixed.** Now `defaults can't set 'type': give each element its own type. (Nothing was changed.)` |
| 10 | Page unit "mm" with px numbers (flowsample) | **Fixed.** `"width":793.7008,"height":1122.5197,"unit":"px"`, note says a viewBox was added. |
| 11 | `placed` coordinates not in page coordinates | **Fixed.** `placed` is now the bbox `[x, y, w, h]` and agrees with `align`/`inspect`. |
| 12 | `sodipodi:docname` set to a temp name | Not checked (would need reading the raw file). |

## Suggestions
- Add a colour summary to `inspect` (distinct fills/strokes, including gradient stops, with ids).
- Add a recolour operation that follows gradients (`from`/`to` colours, or a hue shift, scoped by ids
  or layer). This is the natural "make the car green" call.
- `find {"type": "symbol"}`: return each symbol's size/viewBox. `use` with width/height on a symbol
  without viewBox: scale anyway, or warn. Convert the library's px size into the target document's unit.
- `run_actions`: warn (or refuse) when an action is an extension, since it ignored the selection.
  An `undo` for the last call would make such surprises cheap.
- Write the page after `page_fit` so it reopens without a normalisation note.
- Overlap warnings for new text against existing artwork (or at least a note when `place` targets one
  layer of a multi-layer drawing).
- Return pixel size for PNG exports and bytes for `document_save`.

## Common or task-specific? (input for the next synthesis)
| Need | Seen before? | Guess |
|---|---|---|
| Recolour through gradients / list gradient stop colours | New (last time the tiger had flat fills only) | Common: most detailed illustrations are gradient-shaded |
| Colour summary ("what colours does it use") | Asked for last time as "find by colour"; find now exists, the summary does not | Common for every recolour job |
| Symbol natural size; `use` sizing without viewBox | New | Common for icon libraries, legends, maps |
| `run_actions` extensions ignore selection | New | Task-specific, but dangerous when it happens |
| Clean reopen of saved files (no rounding re-normalise) | New | Common, small |
| Overlap warning against existing artwork | Overlap warnings asked for in 7 earlier reports; this is the foreign-file case | Common |
| flowtext search / full text | Follows old bug 2 | Task-specific: legacy Inkscape files |
| Pixel size / bytes in responses | New | Small, common |
