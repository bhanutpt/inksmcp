"""E24: Mechanics for a `clip` key and a text `halo` key (field reports 5, 8; D-024 step 0).
Questions:
  A. Does query-all report the *clipped* bbox of an element with clip-path?
  B. A clipPath (userSpaceOnUse) on a transformed group: is the clip shape in the group's local
     coordinates? Does transform = inv(CTM(el)) . CTM(ref) put a copy of the reference exactly on it?
  C. When the clipped element is moved with transform-translate (our align/layout path), does the
     clip move with it?
  D. After path-union etc. round trips, does the clipPath survive?
  E. Halo (paint-order stroke): how much does it grow the measured bbox of a text?

Run: uv run python experiments/e24_clip_and_halo.py
"""
from pathlib import Path

from lxml import etree

from inksmcp.document import Document, _q
from inksmcp.engine import Engine
from inksmcp.layout import format_transform, mat_inv, mat_mul

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
eng = Engine()


def clip(doc: Document, el_id: str, ref_id: str) -> str:
    el, ref = doc.get(el_id), doc.get(ref_id)
    defs = next((c for c in doc.root if c.tag == _q("defs")), None)
    if defs is None:
        defs = etree.Element(_q("defs"))
        doc.root.insert(0, defs)
    cp = etree.SubElement(defs, _q("clipPath"))
    cp.set("id", f"clip-{el_id}")
    cp.set("clipPathUnits", "userSpaceOnUse")
    copy = etree.fromstring(etree.tostring(ref))
    copy.attrib.pop("id", None)
    copy.attrib.pop("style", None)
    m = mat_mul(mat_inv(doc._ctm(el)), doc._ctm(ref))
    t = format_transform(m)
    if t:
        copy.set("transform", t)
    else:
        copy.attrib.pop("transform", None)
    cp.append(copy)
    el.set("clip-path", f"url(#clip-{el_id})")
    return t


doc = Document.create(200, 120, "mm")
doc.add({"type": "rect", "id": "panel", "x": 20, "y": 20, "width": 60, "height": 40, "fill": "none",
         "stroke": "#000", "stroke_width": 0.5})
doc.add({"type": "group", "id": "cat", "transform": "translate(50,30) scale(2)"})
doc.add({"type": "circle", "id": "body", "parent": "cat", "cx": 10, "cy": 10, "r": 12, "fill": "#e80"})
print("before  cat bbox", [round(v, 2) for v in eng.bboxes(doc)["cat"]], "(expect 36..76 x 16..56)")
print("B clip transform", clip(doc, "cat", "panel"))
b = eng.bboxes(doc)
print("A after clip   ", [round(v, 2) for v in b["cat"]], "(clipped would be 36..80 x 20..56 -> x 36 w 44, y 20 h 36)")
eng.translate(doc, {"cat": (30, 0)})
b = eng.bboxes(doc)
print("C after move   ", [round(v, 2) for v in b["cat"]], " cat transform:", doc.get("cat").get("transform"))
print("  clip child    ", etree.tostring(doc.root.find(".//" + _q("clipPath"))[0]).decode()[:200])
(OUT / "e24_clip.png").write_bytes(eng.render_png(doc, max_size=600))

d2 = Document.create(100, 60, "mm")
d2.add({"type": "rect", "id": "a", "x": 10, "y": 10, "width": 30, "height": 30, "fill": "#c00"})
d2.add({"type": "rect", "id": "b", "x": 30, "y": 10, "width": 30, "height": 30, "fill": "#00c"})
d2.add({"type": "rect", "id": "frame", "x": 20, "y": 15, "width": 30, "height": 10, "fill": "none"})
clip(d2, "a", "frame")
eng.run_actions(d2, ["path-union"], select=["b"])  # a round trip that doesn't touch `a`
print("D clipPath survives round trip:", d2.get("a").get("clip-path"),
      [round(v, 2) for v in eng.bboxes(d2)["a"]])

d3 = Document.create(100, 60, "mm")
d3.add({"type": "text", "id": "plain", "x": 10, "y": 20, "text": "Halo", "font_size": 8})
d3.add({"type": "text", "id": "halo", "x": 10, "y": 40, "text": "Halo", "font_size": 8,
        "style": {"paint-order": "stroke", "stroke": "#fff", "stroke-width": 2.4, "stroke-linejoin": "round"}})
b = eng.bboxes(d3)
p, h = b["plain"], b["halo"]
print("E plain", [round(v, 2) for v in p], "halo", [round(v, 2) for v in h],
      f"grow w {h[2] - p[2]:.2f} h {h[3] - p[3]:.2f} (stroke width 2.4)")
eng.close()
