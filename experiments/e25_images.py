"""E25: Mechanics for images and file import (D-024 step 1).
Questions:
  A. Which <image> href forms does Inkscape resolve from our temp copy (it lives in a temp folder):
     absolute Windows path, file:/// URI, data: URI? Do query-all and PNG/PDF export see the image?
  B. Does preserveAspectRatio "xMidYMid slice" (cover) / "meet" (contain) / "none" render as in browsers,
     and what bbox does query-all report for each?
  C. An <image> without width/height: what does Inkscape measure?
  D. Can Inkscape export JPEG here (to make a test photo)?

Run: uv run python experiments/e25_images.py
"""
import base64
import time
from pathlib import Path

from lxml import etree

from inksmcp.document import XLINK_NS, Document, _q
from inksmcp.engine import Engine

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
eng = Engine()

# a 200 x 100 px test picture: red left half, blue right half, a black circle in the middle
src = Document.create(200, 100, "px")
src.add({"type": "rect", "x": 0, "y": 0, "width": 100, "height": 100, "fill": "#d00"})
src.add({"type": "rect", "x": 100, "y": 0, "width": 100, "height": 100, "fill": "#00d"})
src.add({"type": "circle", "cx": 100, "cy": 50, "r": 30, "fill": "#000"})
png = OUT / "e25_pic.png"
eng.export(src, png, "png")
try:
    eng.export(src, OUT / "e25_pic.jpg", "jpg")
    print("D jpg export: ok", (OUT / "e25_pic.jpg").stat().st_size, "bytes")
except Exception as e:
    print("D jpg export failed:", str(e)[:120])


def image(doc, id_, href, box=None, par=None):
    el = etree.SubElement(doc.layer("Pics"), _q("image"))
    el.set("id", id_)
    if box:
        for k, v in zip(("x", "y", "width", "height"), box):
            el.set(k, str(v))
    el.set(_q("href", XLINK_NS), href)
    if par:
        el.set("preserveAspectRatio", par)
    return el


forms = {"backslash": str(png.resolve()), "slash": png.resolve().as_posix(), "uri": png.resolve().as_uri(),
         "data": "data:image/png;base64," + base64.b64encode(png.read_bytes()).decode()}
for name, href in forms.items():
    d = Document.create(100, 50, "mm")
    image(d, "img", href, (10, 10, 40, 20))
    try:
        print(f"A {name:9} bbox", [round(v, 2) for v in eng.bboxes(d)["img"]], end="  ")
        size = len(eng.render_png(d, max_size=200))
        print("png bytes", size)
    except Exception as e:
        print(f"A {name:9} FAILED", str(e)[:100])

uri = png.resolve().as_uri()
doc = Document.create(210, 150, "mm")
image(doc, "meet", uri, (10, 50, 40, 40), "xMidYMid meet")
image(doc, "slice", uri, (60, 50, 40, 40), "xMidYMid slice")
image(doc, "none", uri, (110, 50, 40, 40), "none")
image(doc, "nosize", uri, (160, 50))
b = eng.bboxes(doc)
for k in ("meet", "slice", "none", "nosize"):
    print(f"B/C {k:7}", [round(v, 2) for v in b.get(k, ())])
(OUT / "e25_images.png").write_bytes(eng.render_png(doc, max_size=900))
eng.export(doc, OUT / "e25_images.pdf", "pdf")
print("A pdf size", (OUT / "e25_images.pdf").stat().st_size, "(images embedded if >> 2 kB)")

# E: cost of a big embedded image in every round trip
big = Document.create(200, 100, "mm")
blob = base64.b64encode(png.read_bytes() * 1).decode()
image(big, "d", "data:image/png;base64," + blob, (0, 0, 200, 100))
t = time.perf_counter()
eng.bboxes(big)
print(f"E bboxes with a {len(blob) // 1024} kB data URI: {(time.perf_counter() - t) * 1000:.0f} ms")
eng.close()
