"""E21: Mechanics for a `repeat` tool (field report 3). Rows become groups with translate(dx, dy);
mirrored rows reflect shapes with matrix(-1,0,0,1,2X,0) and move texts/groups as blocks.
Questions:
  A. Does query-all measure a reflected polygon inside a translated group correctly?
  B. Does a reflected line keep its arrowhead at the (reflected) end?
  C. Does width-wrapping still work for a text inside a translated group?
  D. Does prepending translate() to a group that already has a transform move it as a block?
  E. Do native connectors attach to shapes inside a translated row group?

Run: uv run python experiments/e21_repeat_mechanics.py
"""
from pathlib import Path

from inksmcp.document import Document
from inksmcp.engine import Engine

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
X = 100  # mirror axis

eng = Engine()
doc = Document.create(200, 120, "mm")
doc.add({"type": "group", "id": "row", "transform": "translate(0,30)"})
doc.add({"type": "polygon", "id": "tri", "parent": "row", "points": [[60, 0], [70, 5], [60, 10]], "fill": "#c00"})
doc.add({"type": "polygon", "id": "tri_m", "parent": "row", "points": [[60, 0], [70, 5], [60, 10]], "fill": "#00c",
         "transform": f"matrix(-1,0,0,1,{2 * X},0)"})
doc.add({"type": "line", "id": "ln_m", "parent": "row", "x1": 20, "y1": 20, "x2": 50, "y2": 20, "stroke": "#000",
         "stroke_width": 1, "marker_end": "arrow", "transform": f"matrix(-1,0,0,1,{2 * X},0)"})
doc.add({"type": "text", "id": "desc", "parent": "row", "x": 10, "y": 40, "font_size": 4, "width": 40,
         "text": "A paragraph that should wrap onto three or four lines inside the row group."})
doc.add({"type": "group", "id": "card", "parent": "row", "transform": "translate(5,0)"})
doc.add({"type": "rect", "id": "card_r", "parent": "card", "x": 10, "y": 60, "width": 40, "height": 15})
doc.add({"type": "circle", "id": "hub", "cx": 150, "cy": 20, "r": 5})
doc.add({"type": "rect", "id": "box", "parent": "row", "x": 140, "y": 50, "width": 20, "height": 10})

lines = eng.wrap_texts(doc, ["desc"])
print("C wrapped lines:", lines)
b = eng.bboxes(doc)
print("A tri   ", b["tri"], "\n  tri_m ", b["tri_m"], "(expect x 130..140, y 30..40)")
print("B ln_m  ", b["ln_m"], "(expect x ~150..180 incl. marker, marker at the left end)")
print("C desc  ", b["desc"], "(expect width <= 40, y from ~67)")
print("D card  ", b["card"], "(expect x 15..55, y 90..105)")
# D: block move by prepending translate — bbox should reflect about X: new x0 = 2X - x1
x0, _, w, _ = b["card"]
delta = 2 * X - (x0 + x0 + w)
g = doc.get("card")
g.set("transform", f"translate({delta:.4f},0) {g.get('transform')}")
print("D after ", eng.bboxes(doc)["card"], f"(expect x {2 * X - x0 - w:.2f}..{2 * X - x0:.2f})")
cid = eng.connect(doc, [{"from": "hub", "to": "box"}])["ids"][0]
print("E conn  ", eng.bboxes(doc)[cid], doc.get(cid).get("d"), "(expect from hub ~y 25 to box top y 80)")
(OUT / "e21_repeat_mechanics.png").write_bytes(eng.render_png(doc, max_size=800))
eng.close()
