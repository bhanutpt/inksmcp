# A3 portrait educational poster: Tamil Alphabet for Beginners
- Date / client / model: 2026-09-28 / Claude Code (desktop app, Code tab) / Claude Opus 5.5.
  Unlike reports 1–3, this one was written by the session that also works on inksmcp. The agent
  used only the MCP tools (no code reading) while drawing, but it knew the tool set from the docs.
- Result files: `out/tamil-alphabet-a3.svg`, `out/tamil-alphabet-a3.pdf` (text to path, 422 kB),
  `out/tamil-alphabet-a3.png` (300 dpi, background `#fffaf0`, 1.18 MB)
- Tool calls (approx.) and time: 13 inkscape tool calls (1 document_create, 2 repeat,
  1 add_elements, 2 update_elements, 1 align, 1 inspect, 2 render_preview, 1 document_save,
  2 export), plus 2 ToolSearch and 1 shell call. Four of the editing calls used `preview: true`,
  so 6 rendered images were looked at in total. About 10 minutes. No errors, no retries.

Task (prompt written first, then executed): an A3 poster teaching the 31 basic Tamil letters to
learners who read Roman script. Every letter gets a card of the same size: the big letter, its
sound, an example word in Tamil, the word's transliteration (IAST extended with ISO 15919 ē ō ḻ ḷ
ṟ ṉ ḵ) and its English meaning.

Result: 297 x 420 mm, mm user units. A maroon title band (Tamil title + English subtitle), then
three colour-coded sections: 12 vowels (red, 2 rows × 6), āytam ஃ (purple, one card plus an
explanation paragraph and a "How to read a card" guide box), 18 consonants with puḷḷi (teal,
3 rows × 6), and a footer (31 basic letters → 247 in total). Cards are 40 x 48 mm on a 45 x 52 mm
pitch. Fonts: Nirmala UI for Tamil, Segoe UI for Roman.

## What worked well
- **`repeat` was ideal for this.** It's a pure card grid: one call per section (12 and 18 rows,
  `columns: 6`, `step: [45, 52]`) drew every card with 7 elements. Ids per template name
  (`letter-1..12`, `sound-…`) made later fixes addressable.
- **Tamil text shaping was correct first time**: conjuncts, vowel signs and puḷḷi dots
  (க், ஞ், ழ்), in Nirmala UI and in the text-to-path PDF. There were no font fallback problems.
  Nirmala UI's Latin glyphs cover ā ḻ ṇ ḵ, so one `text` could mix scripts ("உயிர் எழுத்துக்கள் · Vowels (uyir eḻuttukkaḷ …)").
- **`update_elements` on children of repeat groups works in template (local) coordinates.** The
  same `y: 88` fixed all 12 letters, with no translate arithmetic.
- **Text `width` wrapping + `wrapped_lines`** turned the āytam note into one element. Changing its
  text re-wrapped it automatically.
- **`align` with `to: <rect>`, `vertical: middle`, `text_metrics: visual`, `as_group`** centred
  the note and the two-part guide in the row in one call.
- **`inspect` of the repeat layer** gave each card group's bbox. Every group was 40.5 x 48.5 (the
  card plus its stroke), which proved that no letter overflowed its card without a render.
- **`preview: true` on editing calls** meant 4 of the 6 looks came free with an edit.
  `render_preview` with `region` zoomed in to check descenders and the āytam row.
- The PDF with `text_to_path: true` is ready to send to a print shop without the font.

## What was awkward (agent had to compute, retry, or work around)
- **The vertical layout inside a card was guessed from font metrics I don't know for Tamil.** I set
  baselines by hand (letter 85, sound 91.5, rule 94, word 100, …). Tamil glyphs at 20 mm reach from
  about 12 mm above the baseline (அ) to about 6 mm below it (இ ஏ ஐ). The sound label collided with
  those descenders in 3 of the 12 cards. I only saw it in the zoomed preview. The fix (move the sound
  to the corner, lower the letter to 88) took a 24-item `update_elements`.
- **A per-row exception was found after stamping**: ஔ (au) is ~50 mm wide at 20 mm, so it overflowed
  its 40 mm card on both sides. Fixed with `font_size: 14.5` on `letter-12`. A `"{fs}"` placeholder
  would have worked if I'd known in advance. The general need is "shrink to fit the card width".
- **Correcting the template meant listing every instance.** 12 `sound-n` updates + 12 `letter-n`
  updates, all with the same values. Consonants were stamped after the fix, so they were right first time.
- **Section stacking was computed by hand**: header baselines 59 / 176 / 245, card tops
  64 / 180 / 250, footer 408–414.5. They came from row pitch × rows + gaps. `layout direction: column`
  with each section as an id list might have done it, but sections weren't grouped, and the
  headers must sit a fixed distance above their cards. I didn't try it.
- **The āytam row doesn't fit the grid.** One card + a paragraph + a guide box was built with
  `add_elements` and absolute coordinates copied from the card template (+116 in y). I had to
  keep its 7 offsets in sync with the template by hand.

## Missing tools or options
- **Inline styled runs in text**: highlight the target letter inside the example word (the அ in
  அம்மா) or bold "a" in the guide lines. For example `runs: [{"text": "அ", "fill": "#b03a2e"}, {"text": "ம்மா"}]`,
  becoming tspans. Caution: for Tamil the split must fall on a grapheme-cluster boundary (a vowel
  sign belongs to its consonant).
- **Fit-to-width for text**: `max_width` (shrink the font until the measured width fits) for big
  display glyphs and titles. It would have prevented the ஔ overflow without knowing about it in advance.
- **Stacking inside a block**: "place this text N mm below that element's measured bbox"
  (e.g. `below: "letter", gap: 1.5` in a template). The card's inner rhythm would then follow the
  real glyph extents of any script, instead of hand-picked baselines.
- **Bulk update**: update every instance of a template name (`{"template": "sound", ...}` or an id
  prefix/pattern), or re-run `repeat` on existing groups with a changed template.
- **Overlap/overflow warnings**: `repeat`/`add_elements` could warn when a text's bbox leaves its
  sibling rect or overlaps another text in the same row group. That's the check I did by eye.
- (Open question already in the plan) **font availability**: I assumed Nirmala UI and Segoe UI
  exist (Windows). Nothing warned me, and on another OS the result would silently differ.

## Bugs / surprising behaviour (with the exact call and response)
None. Every call succeeded on its first attempt. Two small notes:
1. `inspect` on a layer of repeat groups shows only group bboxes and child ids, not child bboxes.
   That was enough here (group bbox = card bbox ⇒ no overflow), but finding *which* child
   overflows needs another `inspect layer=<group id>` per card.
2. `align` defaults to `text_metrics: "cap"`. For a multi-line Tamil/Latin paragraph I chose
   `visual` without knowing what "cap height" means for Tamil. The description could say which to
   use for non-Latin scripts and for paragraphs.

## Suggestions
- **Most useful single addition for this task: measured stacking inside templates** (`below`/`gap`
  relative to a sibling's real bbox). It removes the guesswork that caused the only rework.
- Then **text runs** (highlighting letters in words is standard for alphabet charts, flash cards and
  vocabulary sheets) and **`max_width` shrink-to-fit**.
- Bulk update by template name is a cheap way to make "fix the template after the preview"
  one small call.

## Common or task-specific? (input for the synthesis after more field tests)
| Need | Seen before? | Guess |
|---|---|---|
| Stack elements by measured bbox (below/gap) inside a card | Report 3 (card heights by hand, partly solved by `fit_to`) | Common: any card, label or legend with text of unknown height |
| Text runs / mixed styling in one text | Report 2 (bold step numbers, hanging indents) | Common |
| Shrink-to-fit width for text | New | Common for titles, cards and badges |
| Bulk update by template name / id pattern | New (first task that fixed a template after stamping) | Common wherever `repeat` is used |
| Overlap/overflow warnings | Implicit in every report (found by zoomed previews) | Common QA aid |
| Font availability check | Open question in the plan | Common for portability, low urgency on one machine |
| Section stacking (header + grid blocks down a page) | Report 3 (timeline + chart + text columns placed by hand) | Probably common: poster-level layout |
| Grapheme-aware splitting for runs | New | Specific to complex scripts, but required if runs are added |
