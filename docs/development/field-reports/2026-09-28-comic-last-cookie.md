# A4 one-page comic: "The Last Cookie" (6 panels, 2 recurring characters)
- Date / client / model: 2026-09-28 / Claude Code (desktop app, Code tab) / Claude Opus 5.5.
  Written by the session that also works on inksmcp (same caveat as report 4). The drawing used
  MCP tools only; the one exception was a small script for the starburst points.
- Result files: `out/comic-last-cookie.svg`, `out/comic-last-cookie.pdf` (text to path, 101 kB),
  `out/comic-last-cookie.png` (300 dpi, 561 kB)
- Tool calls (approx.) and time: 18 inkscape tool calls for the comic (1 document_create,
  4 add_elements [1 errored], 3 repeat [1 rejected: id clash], 2 update_elements, 1 run_actions,
  1 inspect, 3 render_preview, 1 document_save, 2 export). Plus 4 calls to try to reproduce the
  crash (2 document_create + 2 add_elements), 1 shell call to compute a starburst polygon, 1 grep.
  6 of the editing calls used `preview: true`. About 25 minutes.

Task prompt (written first): an A4 portrait page, title "The Last Cookie", 6 panels of mixed widths
(row 1 2:1, row 2 1:1, row 3 1:2) with white gutters and black borders. Cast: **Mia** (black bob,
yellow dress, blue leggings) and **Biscuit** (orange cat), consistent in every panel. Story:
(1) kitchen, one cookie left, caption "Saturday, 4 p.m.", "The last cookie… all mine!";
(2) DING-DONG! sound effect, "Coming!"; (3) Biscuit beside the jar, thought bubble "Unattended cookie
detected."; (4) empty jar, lid off, crumbs, "BISCUIT?!"; (5) close-up of an innocent Biscuit with
crumbs, cropped by the panel, "Meow?"; (6) caption "Luckily, the doorbell was Grandma — with a fresh
batch!", plate of cookies, "Okay, okay… we share." / "Purrr ♥", THE END.

Result: every beat of the prompt is on the page. Mia appears 4 times (smile + pointing, surprised,
shocked with arms up, grinning with hands on hips) and Biscuit 3 times (normal, close-up 2.2×
clipped to the panel, content with eyes shut). There are 7 balloons (6 speech + 1 thought), 2
captions, 1 SFX starburst, and 6 frames. Layers: Title, Backgrounds, Props, SFX, Captions,
Characters, Balloons, Frames. Font: Comic Sans MS.

## What worked well
- **`repeat` works as a character component system.** The template is a group with
  `transform: "translate({x},{y}) scale({s})"` and `step: [0, 0]`. Each row is one appearance. Pose
  parts are placeholders in the character's local coordinates: `"d": "{arms}"`, `"d": "{mouth}"`,
  `"fill": "{mfill}"`, `"r": "{eye}"`. One call drew all 4 Mias (15 parts each) and one drew all 3
  Biscuits (20 parts each). They are on-model and addressable (`mouth-3`, `hair_back-2`). Scaling
  the close-up needed nothing special.
- **Clipping through the escape hatch worked first time**: a rect over the panel, then
  `run_actions select: ["cat_row-2", "p5_clip"], actions: ["object-set-clip"]`. The body and tail are
  cropped at the frame, in the preview and in the PDF.
- **Balloons from `fit_to`**: each balloon is a text + a rect (`fit_to`, `fit_padding`, `rx`). The
  response's `fitted` bboxes gave me the edges for the tails. The tail is an open `polyline`
  filled white: the fill covers the balloon border at the root and the stroke draws only the two
  sides. That gives a clean join with no union, one element per tail.
- **`defaults` with `layer`** made the 14-element balloon batch and the 14-element tails/frames
  batch short.
- **Off-page warning** on the close-up cat (`'cat_row-2' extends beyond the page (bottom by 4.65 mm)`):
  here it was intended (to be clipped), but it's the right kind of hint.
- **Error for the id clash was precise** (`rows[0], mia: Id 'mia-1' already exists.`) and nothing was
  written.
- Layers as z-order (props < characters < balloons < frames) needed no `z_order` call.

## What was awkward (agent had to compute, retry, or work around)
- **Balloon tails and thought-bubble dots: every tip was computed by hand.** Target = character
  position + local head/mouth offset × scale, e.g. Mia in panel 2: (152, 110 − 47 × 0.85). Base = the
  fitted rect's bottom edge − 0.6. That was 6 tails + 2 dots. There is no way to say "point at
  `head-2`" or "at the mouth of `mia-2`".
- **Panel geometry was typed three times.** The same 6 rects appear as backgrounds, as frames, and
  (for panel 5) as the clip rect. The mixed-width row splits (124 + 4 + 62, 93 + 4 + 93, 62 + 4 + 124)
  were worked out by hand from the page width and gutter.
- **Props were placed by absolute coordinates per panel.** The counter + jar + lid appear 3 times at
  different positions. Each object sitting on the counter needed its y worked out from the counter
  top (jar 153..173 on a top at 173; cat feet at 173).
- **Starburst polygon** (28 points for DING-DONG!) was computed with a Python one-liner. There's no
  star / regular-polygon shape.
- **Fixing the character after stamping**: the hair read as a hood, so I changed
  `hair_back-1..4` one by one (same values ×4). This is the second report in a row that needs a bulk
  update by template name.
- **id_prefix vs template id clash** (`id_prefix: "mia"` + template group `id: "mia"` → both give
  `mia-1`). It's my mistake, but a natural one. The tool could suffix the row groups
  differently, or the description could warn about it.
- **Clipping needs Inkscape knowledge**: the action name `object-set-clip`, "topmost selected object
  becomes the clip", and making sure the clip rect is above the target in z-order. None of this is
  in the tool descriptions.

## Missing tools or options
- **Callout / balloon element**: text + fitted box + a tail that points at an element id (or a
  point), e.g. `{"type": "balloon", "text": "...", "at": [x, y] | "below": ..., "tail_to": "mouth-2",
  "style": "speech|thought|shout|caption"}`. The tail's root would be placed on the box edge
  nearest the target. Thought style would draw a trail of dots.
- **Anchor points on components**: named points in a template (`"anchors": {"mouth": [0, -47]}`),
  resolved per instance so tails and connectors can target `mia-2.mouth`.
- **Panel / region splitter**: rows with ratios and a gutter inside a rect → returns panel rects
  (optionally background, frame and clip in one go), e.g. `panels(rect, rows=[[2,1],[1,1],[1,2]], gutter=4)`.
- **`clip` as an element key** (`"clip": "panel-5"` or `"clip": [x, y, w, h]`) instead of
  `run_actions`. Image import will need the same.
- **Star / regular polygon shape**: `{"type": "star", "cx", "cy", "points": 14, "r1", "r2"}`
  (+ `ry` scale) for bursts, badges and seals.
- **Bulk update by template name** (again, see report 4).
- **"Sit on" placement**: put an element's bottom on another element's top (`on: "p3_top"`), for
  props and characters standing on counters and floors.

## Bugs / surprising behaviour (with the exact call and response)
1. **Intermittent shell crash leaves the document half-updated (add_elements is not all-or-nothing).**
   The first `add_elements` of the page (37 elements: title, 6 panel backgrounds, props, a 28-point
   polygon, a text with `vertical_anchor: "middle"`, 2 rects with `fit_to`, 1 text with `width: 62`;
   `preview: true`) returned:
   `Error executing tool add_elements: Inkscape shell exited unexpectedly: InkscapeApplication::close_document: No document!`
   `Magick: quitting due to signal 51 (SIGTERM) "Terminated"...`
   `inspect` then showed **all 37 elements written**, but the steps that need measuring had not run.
   The caption rects had no size (`fit_to` not applied), the 62 mm text was not wrapped, and the
   SFX text was not vertically centred. Re-running `update_elements [{"id":"p6_cap","width":62},
   {"id":"p2_sfx",...,"vertical_anchor":"middle"},{"id":"p1_cap_box"},{"id":"p6_cap_box"}]` fixed it
   (`fitted`, `wrapped_lines` returned), so the server restarted the shell itself.
   **Not reproducible:** the identical 37-element call succeeded in two fresh documents (doc3 with a
   6-element subset, doc4 with the full call). The failing call was the first measurement in a new
   document (doc2), made while doc1 was still open.
   Two problems: (a) the shell dies intermittently (cause unknown: the message suggests a document
   was closed that the shell didn't have; the SIGTERM comes from the server's shutdown of the dead
   process or from ImageMagick); (b) on a shell failure the XML changes are kept but the error doesn't
   say so, and the post-processing is silently skipped. Expected: roll back, or report
   "written, but wrapping/fitting/anchoring not applied: re-run update_elements on …".
   Per D-021, this is a bug to fix right away (not deferred to the synthesis).
2. (Minor) `repeat`'s off-page warning doesn't know about later clipping. That's expected; just noting
   that a warning for intended bleed is normal in comics.

## Suggestions
- **Fix bug 1 first**: make add/update/repeat atomic across a shell failure (keep a copy of the tree;
  restore it on error, or retry once on a fresh shell), and find what kills the shell (log the shell's
  last command and stderr).
- Most useful addition for comics: **a balloon/callout element with `tail_to` an element or anchor**.
  It removes all the hand-computed tails and dots, and callouts are also used in infographics.
- Then a **`clip` key**, **component anchors**, and a **panel splitter**.

## Common or task-specific? (input for the round-2 synthesis)
| Need | Seen before? | Guess |
|---|---|---|
| Atomic writes / clear partial-failure reporting | New (first crash in any report) | Common: correctness, fix now (D-021) |
| Bulk update by template name | Report 4 | Common (2 of 2 `repeat`-heavy tasks) |
| Callout with a pointer to an element (balloon tail) | Report 2 (labels beside lines), report 3 (annotations) | Common core; speech/thought/shout styles are comic-specific |
| Named anchors on components / parts of groups | New | Common wherever components are reused (icons, characters, diagrams) |
| `clip` as an element key | Comic memory (2026-09-27) predicted it | Common (panels, image crops, chart plot areas) |
| Split a region into rows/columns by ratios with gutters | Report 3 (columns by hand), report 4 (sections by hand) | Common: page layout; "panels" is the comic name for it |
| Star / regular polygon shape | Report 2 (block arrows by hand) | Common for badges, seals and icons |
| Place on top of another element ("sit on") | New | Probably common for illustrations; low priority |
| Parametric components via `repeat` + placeholders | Report 3's timeline cards | Works today; a named reusable component (instantiate later, one at a time) would generalise it |
