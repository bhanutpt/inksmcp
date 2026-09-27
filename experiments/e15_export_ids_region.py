"""E15: From field report 2026-09-27-log-graph-a4.

A. What does Inkscape do with several export ids (export-id:a,b + export-id-only)? One file per id?
B. export-area:x0:y0:x1:y1 — which units (px or user units)? Everything visible?
C. Is export-area relative to the viewBox origin?

Run: uv run python experiments/e15_export_ids_region.py
"""
import struct
from pathlib import Path

from inksmcp.document import Document
from inksmcp.engine import EXPORT_BASELINE, Engine

OUT = Path(__file__).parent / "out" / "e15"
OUT.mkdir(parents=True, exist_ok=True)
eng = Engine()


def size(p: Path):
    return struct.unpack(">II", p.read_bytes()[16:24])


doc = Document.create(100, 50, "mm", background="#ffffff")
doc.add({"type": "rect", "id": "a", "x": 10, "y": 10, "width": 20, "height": 20, "fill": "red"})
doc.add({"type": "rect", "id": "b", "x": 60, "y": 20, "width": 20, "height": 20, "fill": "blue"})

src = eng._open(doc)
for f in OUT.glob("*.png"):
    f.unlink()
r = eng.shell.run(";".join(EXPORT_BASELINE + ["export-id:a,b", "export-id-only:true", "export-area-drawing",
                                              f"export-filename:{OUT / 'multi.png'}", "export-type:png",
                                              "export-do"]), check=False)
print("A. files:", sorted(p.name for p in OUT.glob("*.png")), r.messages)
for p in sorted(OUT.glob("*.png")):
    print("  ", p.name, size(p))

for name, area in [("user", "10:10:30:30"), ("px", "37.795:37.795:113.386:113.386")]:
    out = OUT / f"area_{name}.png"
    r = eng.shell.run(";".join(EXPORT_BASELINE + [f"export-area:{area}", f"export-filename:{out}",
                                                  "export-type:png", "export-do"]), check=False)
    print(f"B. export-area {name:4s} {area:32s} ->", size(out) if out.exists() else "MISSING", r.messages)
eng._close(src)

# C. non-zero viewBox origin
doc.root.set("viewBox", "10 10 100 50")
src = eng._open(doc)
out = OUT / "area_origin.png"
eng.shell.run(";".join(EXPORT_BASELINE + ["export-area:0:0:75.59:75.59", f"export-filename:{out}",
                                          "export-type:png", "export-do"]), check=False)
eng._close(src)
print("C. origin-shifted doc, area 0:0:75.59:75.59 px ->", size(out))
eng.close()
