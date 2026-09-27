"""E07: Groundwork for `align`.

A. Does `object-align` work in --shell (no desktop)? What does it change (x/y or transform)?
B. What units does `transform-translate` use in a mm document?
C. Can we measure font metrics (cap height, descender) by querying probe texts?
   Is cap height proportional to font size (one probe per font is enough)?
D. Does Inkscape honour `dominant-baseline` when measuring/rendering?

Run: uv run python experiments/e07_align_and_text_metrics.py
"""
from pathlib import Path

from inksmcp.document import Document
from inksmcp.engine import Engine

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
eng = Engine()


def show(doc, ids):
    b = eng.bboxes(doc)
    for i in ids:
        el = doc.get(i)
        attrs = {k: el.get(k) for k in ("x", "y", "cx", "cy", "transform") if el.get(k) is not None}
        print(f"   {i:6s} bbox={tuple(round(v, 2) for v in b[i])} attrs={attrs}")


def base():
    doc = Document.create(100, 100, "mm")
    doc.add({"type": "rect", "id": "box", "x": 10, "y": 10, "width": 60, "height": 30, "fill": "#ddd"})
    doc.add({"type": "circle", "id": "dot", "cx": 80, "cy": 70, "r": 5, "fill": "red"})
    doc.add({"type": "text", "id": "txt", "x": 20, "y": 80, "text": "Client", "font_size": 6})
    return doc


print("A. object-align in shell")
for arg in ["hcenter last", "vcenter last", "left page", "right first"]:
    doc = base()
    try:
        msgs = eng.run_actions(doc, [f"object-align:{arg}"], select=["dot", "txt", "box"])
        print(f" object-align:{arg}  messages={msgs}")
        show(doc, ["dot", "txt", "box"])
    except Exception as e:
        print(f" object-align:{arg}  FAILED {e}")

print("\nB. transform-translate units (mm doc, translate 10,0)")
doc = base()
eng.run_actions(doc, ["transform-translate:10,0"], select=["dot", "txt"])
show(doc, ["dot", "txt"])

print("\nC. font metrics via probe texts")
doc = Document.create(200, 200, "mm")
probes = {}
for fam in ["sans-serif", "serif"]:
    for size in [5, 10, 20]:
        for s in ["H", "x", "Hg", "Client", "inksmcp"]:
            pid = f"p_{fam}_{size}_{s}".replace("-", "")
            doc.add({"type": "text", "id": pid, "x": 10, "y": 100, "text": s, "font_size": size, "font_family": fam})
            probes[pid] = (fam, size, s)
b = eng.bboxes(doc)
for pid, (fam, size, s) in probes.items():
    x, y, w, h = b[pid]
    top, bottom = 100 - y, (y + h) - 100  # above / below baseline
    print(f"   {fam:10s} {size:3d} {s:8s} above={top / size:.3f}em below={bottom / size:.3f}em")

print("\nD. dominant-baseline")
doc = Document.create(100, 100, "mm")
for db in ["auto", "central", "middle", "hanging"]:
    doc.add({"type": "text", "id": f"d_{db}", "x": 10, "y": 50, "text": "Hx", "font_size": 10,
             "style": f"dominant-baseline:{db}"})
b = eng.bboxes(doc)
for db in ["auto", "central", "middle", "hanging"]:
    print(f"   {db:8s} bbox={tuple(round(v, 2) for v in b[f'd_{db}'])}")
eng.close()
