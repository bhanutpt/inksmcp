"""E11: Groundwork for `page_fit`.

A. What does `page-fit-to-selection` change headless (width/height/viewBox/content transforms)?
B. Are units (mm) preserved?
C. With a non-zero viewBox origin, what do query-all bboxes report?
D. What happens with a full-page background rect / with layers?

Run: uv run python experiments/e11_page_fit.py
"""
from pathlib import Path

from inksmcp.document import Document
from inksmcp.engine import Engine

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
eng = Engine()


def attrs(doc, *ids):
    r = doc.root
    print("   root:", {k: r.get(k) for k in ("width", "height", "viewBox")})
    for i in ids:
        el = doc.get(i)
        print(f"   {i}:", {k: el.get(k) for k in ("x", "y", "width", "height", "transform") if el.get(k)})


def make():
    doc = Document.create(200, 150, "mm", background="#ffffff")
    doc.add({"type": "rect", "id": "a", "x": 40, "y": 30, "width": 30, "height": 20, "fill": "#39f", "layer": "L"})
    doc.add({"type": "rect", "id": "b", "x": 100, "y": 70, "width": 20, "height": 30, "fill": "#f93", "layer": "L"})
    return doc


print("A/B/D. page-fit-to-selection with a,b selected")
doc = make()
eng.run_actions(doc, ["page-fit-to-selection"], select=["a", "b"])
attrs(doc, "a", "b", "background")
lay = doc.layers()[0]
print("   layer transform:", lay.get("transform"))
print("   bboxes:", {k: tuple(round(v, 2) for v in b) for k, b in eng.bboxes(doc).items() if k in ("a", "b", "background")})
eng.export(doc, OUT / "e11_fit_selection.png", width=400, background="#ddd")

print("\nA'. page-fit-to-selection with nothing selected (drawing incl. background)")
doc = make()
eng.run_actions(doc, ["select-clear", "page-fit-to-selection"])
attrs(doc, "a")

print("\nC. manual non-zero viewBox origin: viewBox='30 20 100 90', width=100mm")
doc = make()
doc.root.set("viewBox", "30 20 100 90")
doc.root.set("width", "100mm")
doc.root.set("height", "90mm")
raw = eng.shell
src = eng._open(doc)
out = raw.run("query-all").output
eng._close(src)
print("   raw query-all:", [l for l in out.splitlines() if l.startswith(("a,", "b,"))])
print("   our bboxes():", {k: tuple(round(v, 2) for v in b) for k, b in eng.bboxes(doc).items() if k in ("a", "b")})
eng.export(doc, OUT / "e11_origin.png", width=400, background="#ddd")
eng.close()
