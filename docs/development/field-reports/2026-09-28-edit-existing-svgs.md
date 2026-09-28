# Editing SVG files someone else made: flowsample, tiger.svgz, Inkscape logo, NPS symbol library
- Date / client / model: 2026-09-28 / Claude Code subagent / Claude Opus 5.5 (claude-opus-5-5).
  Field tester only: I did not read the server's source, docs or tests. I learned the tools from
  their descriptions and responses. Server 0.2.0, Inkscape 1.4.4.
- Result files (all in `out/edit-test/`):
  - Job 1: `flowsample-edited.svg`, `flowsample-edited.png` (96 dpi, 84 kB)
  - Job 2: `tiger-edited.svg`, `tiger-edited.pdf` (41 kB), `tiger-head.png` (600 x 563 px).
    `tiger.svg` is an uncompressed copy of `tiger.svgz` that I made with `gunzip -c` (see bug 1).
  - Job 3: `logo-dark.svg`, `logo-dark.png` (512 px), `park-legend-a6.svg`, `park-legend-a6.png` (150 dpi)
- Tool calls (approx.) and time: about 100 inkscape tool calls, 14 shell/Read calls, about 35 minutes.
  - Job 1: 21 calls (4 errors, 1 of them an Inkscape crash). 1 Read of the raw file, 2 `ls`.
  - Job 2: 43 calls (4 errors: 3 x `.svgz` open, 1 action not found). 5 shell calls (gunzip, 3 greps, 1 sed).
    About 8 of the calls were redone work after the server restart (see below).
  - Job 3: 33 calls (logo 9, legend 24; 4 errors: 1 bad `defaults`, 3 `run_actions`). 3 greps of the raw library.
  - 17 of the calls were `render_preview` (or `preview: true`), mostly to identify parts of the tiger.
- **Server restart (not a server bug):** my session was cut off by a network error in the middle of
  Job 2. The MCP server was restarted, so all open documents were gone (`inkscape_info` →
  `"documents":{}`). Job 1 was already saved and exported. The tiger's eye recolour and banner were
  not saved yet, so I reopened `tiger.svg` and redid them (2 calls, same ids).

## The three jobs and what came out
- **Job 1.** `flowsample.svg` is **not a flowchart**. It is Inkscape's old *flowed text* sample: one
  `flowRoot` (`flowRoot908`) with two `flowRegion` shapes, a `flowRegionExclude`, and three `flowDiv`
  paragraphs (English, Arabic, English), at the root of the document with no layer. There were no boxes
  or labels to change. What I did: I kept the flowed text, moved it to the bottom of the page with
  `align`, and drew the requested flowchart (Order received → Check stock → In stock? → Ship /
  Back-order) in the empty top half. Then I saved, **reopened the saved file** and did the "editing"
  part there: recoloured all boxes to one teal palette with one `update_elements`, and added
  "Send invoice" under "Ship" with `place` + `connect`. So "edit someone else's flowchart" was only
  tested on a file this server wrote. The foreign part of the file (the flowed text) could be moved
  but not edited or recoloured.
- **Job 2.** Finished. Eyes (green irises `path118`, `path130` and darker tops `path119`, `path161`,
  `path162`) recoloured to blue. A dark "TIGER" banner sits 16 px below the head. Page fitted with a 20 px
  margin. PDF and a 600 px head crop exported. The page fit needed a raw file edit (bug 4).
- **Job 3.** Finished. Logo on a `#34425e` rounded square (176.56 x 176.56 px) with a white bold
  "Inkscape" label. A6 legend: title, 6 framed NPS icons (Campground, Drinking water, Picnic area,
  Parking, Restrooms, Trailhead) in a 2 x 3 grid with labels, and a credit line.

## What worked well
- **`render_preview` with `ids` + `only_ids` is a good "what is this path?" tool.** The tiger has
  about 300 anonymous paths. I found the eyes by zooming on candidate ids (from `inspect` bboxes) and
  drawing them alone: 5 small previews found the 5 eye paths.
- **`update_elements` fill beats presentation attributes.** The tiger stores colours as
  `fill="rgb(153,204,50)"`. Setting `fill` added a style that won. No need to know how the file stores it.
- **`place: {"below": "g3", ...}` worked against a foreign group** with a nested
  `matrix(1.1,0,0,-1.1,-110,1140)` (flipped y). The banner landed centred, 16 px under the real
  visual bottom.
- **`fit_to` around a gradient-heavy foreign group** (`g9139`, the logo) plus a new label made the
  dark square in one call. Changing `fit_padding` later re-fitted it (portrait → square).
- **`z_order below` a target** moved the new background out of its own layer to the root, under the
  logo, in one call, and said where it went.
- **Connectors survive save + reopen.** After reopening `flowsample-edited.svg` the outline listed
  `connector2` with `"from":"s1","to":"s2"`, and new `connect` calls worked next to the old ones.
- **`align` works on an unsupported element type.** `flowRoot908` could not be updated or inspected,
  but `align` moved it (dx 96.9, dy 397.7) and returned its bbox.
- **`import_file` of the symbol library** returned a full `renamed` map of the 103 symbol ids, and
  `move_to_layer` pulled 6 icons out of it at their visual positions.
- **`layout` grid of `[icon, label]` pairs** made the legend grid in one call, centred on the page.
- **Crash handling is good.** Inkscape crashed on a raw action (bug 3). The server restarted the
  shell, retried, and reported `(Nothing was changed.)`. The document was still usable.
- `export` with `region` + `width: 600` gave exactly the head crop I previewed.

## What was awkward (agent had to compute, retry, or work around)
- **I had to read the raw `flowsample.svg` to find out what it was**, because `document_open` and
  `inspect` returned an empty outline (bug 2). Without the raw file I would not have known the ids.
- **Finding the eyes took about 10 calls.** `inspect` shows no fill for the tiger paths (bug 5), so I
  could not search for "green". I estimated positions from a preview, picked ids by bbox, then zoomed.
  A colour search ("which ids use rgb(153,204,50)?") would have been one call.
- **Choosing icons from the symbol library was by grid position, by hand.** `inspect` lists 99 `use`
  elements with bboxes but not which symbol each one shows (`href`). I mapped "column 7, framed row
  1 → Campground_Inv" from the preview, then looked up the id. There is no way to place a symbol
  by name (`add_elements` has no `use` type), so I imported the whole library, moved 6 uses out and
  deleted the rest.
- **The first icon pick was wrong** (bug 7): ids that the server invents for id-less elements differ
  between `document_open` and `import_file`. I took ids from the opened library and used them in the
  imported copy. I got the plain icons instead of the framed ones, and "Parking" was invisible.
  Cost: 1 delete, 1 re-import, 1 inspect, 1 move, 1 add (5 calls).
- **The .svgz file needed `gunzip` in the shell** (bug 1).
- **The tiger page fit needed `sed` on the saved file** (bug 4): I replaced `width="154.6669mm"` and
  `height="243.08mm"` with `584.568` / `687.499`, reopened, and ran `page_fit` again. Before that I tried
  `page_resize`, `run_actions page-fit-to-selection` and a re-import into a new document. None fixed it.
- **The banner and its text picked up a black stroke** from the tiger's root `<svg stroke="rgb(0,0,0)">`.
  I only noticed because the bbox came back 421 x 71 instead of 420 x 70. Fixed with `stroke: "none"`.
- Hand computations: flowchart box positions and the diamond points; the head crop region
  (`[40, 20, 525, 475]`, 2 tries by eye); the square padding for the logo background
  (`(176.56 − 128.34) / 2 = 24.11`).

## Missing tools or options
- **Find elements by style**: e.g. `inspect` with `fill: "#99cc32"` or "list the distinct fills and
  which ids use them". This is the natural first step when recolouring a drawing someone else made.
- **`inspect` should show what a `<use>` points to** (`href: "#Parking_Inv"`) and list `<symbol>`s in
  defs by id and title.
- **Place a symbol by name**: e.g. an element type `use` with `href` (and x/y/width), or
  `import_file` of one symbol id from a library file. Then the legend is one `repeat` call.
- **Flowed text (`flowRoot`) support**: at least list it in the outline with its text, allow
  `text`/`fill` updates, or offer a safe "convert to normal text" (the raw action crashes Inkscape).
- **Remove unused defs** (vacuum). The legend file has 206 symbols and uses 6 (170 kB).
  `run_actions vacuum-defs` → "could not find action", and `file-cleanup` → "not allowed here".
- **Normalise the page of a foreign file**: a way to set the root `width`/`height` units, or have
  `page_fit`/`page_resize` always write a uniform scale.
- **Open `.svgz`** (or at least a clear error).

## Bugs / surprising behaviour (with the exact call and response)
1. **`.svgz` cannot be opened, and the error is empty.** `document_open {"path":
   "C:\\drv\\ai\\inksmcp\\out\\edit-test\\tiger.svgz"}` → `Error executing tool document_open` (no
   message). Three times, 2 before and 1 after the server restart. The same file gunzipped to `tiger.svg`
   opened fine. So `tiger.svg` in `out/edit-test` exists because I ran `gunzip -c tiger.svgz > tiger.svg`
   in the shell. `document_open` did **not** handle the `.svgz` directly.
2. **`flowRoot` content is invisible to the outline.** `document_open flowsample.svg` →
   `{"doc_id":"doc1","page":{...},"outline":[]}`. The file has `flowRoot908` at the root.
   `inspect {"layer": "flowRoot908", "max_children": 100}` → `No layer named 'flowRoot908'.
   (Nothing was changed.)`. Root-level groups are listed (the tiger's `g3`, the library's 99 loose
   `use`s, as a summary), so this looks specific to `flowRoot`. After I added a layer, the reopened
   file's outline showed only my layer; the flowed text is still in the file but not listed.
   Also: `update_elements [{"id": "flowDiv17", "text": "..."}]` → `Cannot update element of type
   'flowDiv' yet.`; same for `flowRoot` (`Cannot update element of type 'flowRoot' yet.`).
3. **Raw action crashes Inkscape.** `run_actions {"select": ["flowRoot908"], "actions":
   ["text-convert-to-regular"]}` → `Inkscape shell exited unexpectedly (exit code 3221225477) while
   running 'text-convert-to-regular': Emergency save activated! ...` with `flowtext_to_text() in
   ...libinkscape_base.dll` in the stack, `... (again after a restart) (Nothing was changed.)`.
   This is an Inkscape bug, but the server handled it well. (The old name `object-flowtext-to-text` →
   `could not find action for: object-flowtext-to-text`.)
4. **`page_fit` gives a non-uniform page on the tiger.** The original root is `width="100%"
   height="297mm" viewBox="0 0 594 840"`. `document_open` reports `"width":594.0,"height":840.0,"unit":"px"`,
   but the page preview is 434 x 800 px, so Inkscape's page is not 594 x 840. `page_fit {"margin": 20}`
   → `{"page":{"width":584.568,"height":687.499,"unit":"px"},"content_moved_by":[28.307,-217.894]}` and the
   saved root was `width="584.568" viewBox="0 0 584.568 687.499" height="243.08mm"`. 243.08 mm is
   918.7 px, so the y scale (1.336) differs from the x scale (1.0). The preview had a white band at the
   bottom, and then `page_resize` warned `'g3' extends beyond the page (top by 5.65 px).` (the tiger was
   placed 20 px from the top, then measured 25.65 px higher). After `run_actions page-fit-to-selection` and
   `page_fit` again the root became `width="154.6669mm" height="243.08mm"`, and the response said `"unit":"mm"`
   for the same 584.568 x 687.499. Still non-uniform. Only a `sed` of the two attributes fixed it.
5. **`inspect` shows no fill/stroke for presentation attributes.** The tiger's paths use
   `fill="rgb(...)"` attributes (226 of them, no `style`). `inspect {"layer": "g4"}` lists every path with a
   bbox but no `fill`. The flowchart elements (style-based) do show `fill`.
6. **`import_file` drops the imported root's presentation style and can scale non-uniformly.**
   (a) `import_file tiger-edited.svg` into a new px document → `"scale":[1.0,1.336333]` (bug 4's page), and
   the tiger rendered with black fills because the root's `fill="none" stroke="rgb(0,0,0)"` was not carried
   onto the wrapper group. (b) The NPS library root has `style="fill:black;stroke:black"`. After import, the
   plain `Parking` symbol (stroke only, stroke inherited from the root) was invisible.
7. **Ids invented for id-less elements are not stable.** In the opened library, `use510` (bbox
   504,72,72,72) is `Campground_Inv`. In the imported copy, `use510` was the plain `Campground` (bbox
   15.08 x 12.96 mm). A second import numbered them `use1096..use1200`. Nothing warns about this.
8. **Imported defs stay after the group is deleted, and a second import prefixes everything.**
   `delete_elements ["lib"]` → `{"deleted":["lib"]}`, but the 103 symbols stayed. The second import
   answered with 103 renames (`"Parking_Inv":"lib-Parking_Inv"`, ...). The saved legend has 206
   `<symbol>` and references 6 (+ 4 `ear` helpers).
9. **Misleading `defaults` error.** `add_elements {"defaults": {"layer": "Icons", "type": "text", "x": 0,
   "y": 0, "font_size": 4.2, ...}, "elements": [{"id": "title", "text": "Park facilities", ...}, ...]}` →
   `defaults keys ['layer', 'type', 'x', 'y', 'font_size', 'font_family', 'fill', 'text_anchor'] are not
   valid for any element type in this batch. (Nothing was changed.)`. The real problem was `type` in
   `defaults` (so the elements had no type). The message blames all keys.
10. **Page unit "mm" with px numbers.** `flowsample.svg` has `width="210mm" height="297mm"` and no
    viewBox. `document_open` → `"page":{"width":793.7007874015749,"height":1122.5196850393702,"unit":"mm"}`.
    User units are px here (a 140-wide rect was 140 px), so "mm" is wrong.
11. **`placed` coordinates are not in page coordinates.** Tiger banner: `"placed":{"banner":[53.977,674.633]}`
    but `inspect` gave its bbox `[53.48,815.39,421.0,71.0]` (the new layer is not transformed at that point).
    In the legend `"placed":{"lab1":[142.925,43.792]}` for a label whose icon was at x 133..152. I could not
    tell what these numbers mean; the preview was right.
12. Small: saved files get `sodipodi:docname` set to a temp name (`"14ae192b9398.svg"`,
    `"0428ac3fac7a.svg"`) instead of the real file name.

## Suggestions
- Fix `.svgz` open (gunzip on load; save back as `.svgz` only if asked), and never return an empty error.
- Normalise foreign page geometry on open: if `width`/`height`/`viewBox` give different x and y scales
  (or `width="100%"`), warn and offer a fix; make `page_fit`/`page_resize` always write a uniform scale.
- In `inspect`, report the computed fill/stroke (attributes, style and inheritance), `href` for `use`,
  and `flowRoot` with its text. Add a style filter (`fill`, `stroke`, `type`).
- In `import_file`, copy the source root's presentation attributes/style onto the wrapper group, and
  optionally import only named symbols (`symbols: ["Parking_Inv", ...]`) or place one with a `use` element.
- Warn when new elements inherit a stroke/fill from the root (`<svg stroke=...>`) that the caller did not set.
- Give invented ids a note in the `document_open` response ("ids use495..use599 were assigned; they
  are not in the file"), or keep them in the saved file so they are stable.
- A `vacuum_defs` option on `document_save` or `delete_elements`.

## Common or task-specific? (input for the next synthesis)
| Need | Seen before? | Guess |
|---|---|---|
| Open `.svgz` | New | Common for files from the web and old Inkscape samples |
| Uniform page scale on foreign files (`width="100%"`, mm height + px viewBox) | New | Common: any file not made by this server |
| `inspect` shows computed fills; find elements by colour | New | Common for every "recolour X" edit |
| `use` href / symbol listing; place a symbol by name | New as far as I know (the route-map report drew its map symbols with `repeat`) | Common for legends, maps, icon sheets |
| Root style carried into `import_file` | New | Common: many hand-made SVGs set fill/stroke on the root |
| Stable ids for id-less elements | New | Common when editing foreign files |
| Vacuum unused defs | New | Common after imports |
| flowRoot (SVG 1.2 flowed text) support | New | Task-specific: legacy Inkscape files only |
| Clearer `defaults` error | New | Small, common |
