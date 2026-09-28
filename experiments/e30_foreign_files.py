"""E30: Editing SVGs someone else made (field report 2026-09-28-edit-existing-svgs).

Questions:
  A. What does opening a .svgz give, and why was the tool error empty?
  B. How does Inkscape size a page with width="100%" height="297mm" viewBox="0 0 594 840" (the tiger)?
     Does it scale the viewBox uniformly (preserveAspectRatio meet) or per axis, as our model assumes?
  C. The same for absolute width/height whose aspect differs from the viewBox.
  D. No viewBox (flowsample: width="210mm"): what is a user unit?
  E. Ids for id-less elements: document_open vs import_file of the same file.

Inputs: copies of files that ship with Inkscape (share/inkscape/examples, symbols), in out/edit-test/.
Run: uv run --no-sync python experiments/e30_foreign_files.py
"""
import gzip
import struct
from pathlib import Path

from lxml import etree

from inksmcp.document import Document
from inksmcp.engine import Engine
from inksmcp.inkscape import InkscapeShell

SRC = Path(__file__).parents[1] / "out" / "edit-test"
OUT = Path(__file__).parent / "out"


def png_size(p: Path) -> tuple[int, int]:
    return struct.unpack(">II", p.read_bytes()[16:24])


def page_px(eng: Engine, svg: bytes, name: str) -> tuple[int, int]:
    """Inkscape's page size in px: export the page at 96 dpi and read the PNG header."""
    doc = Document.from_bytes(svg)
    out = eng.export(doc, OUT / f"e30_{name}.png", "png", area="page", dpi=96)
    return png_size(out)


def main():
    OUT.mkdir(exist_ok=True)
    # A -------------------------------------------------------------------------------------------
    data = (SRC / "tiger.svgz").read_bytes()
    print("A magic:", data[:2].hex())
    try:
        Document.from_bytes(data)
    except Exception as e:
        print("A open .svgz ->", type(e).__name__, repr(str(e))[:80])
    tiger = gzip.decompress(data)
    root = etree.fromstring(tiger)
    print("A tiger root:", {k: root.get(k) for k in ("width", "height", "viewBox", "preserveAspectRatio", "fill", "stroke")})

    with InkscapeShell() as sh:
        eng = Engine(sh)
        # B -----------------------------------------------------------------------------------------
        print("B tiger page px:", page_px(eng, tiger, "tiger"), "(A4 portrait = 794 x 1123)")
        doc = Document.from_bytes(tiger)
        print("B our model: viewbox", doc.viewbox, "px/uu", doc.px_per_user_unit, "unit", doc.unit)
        b = eng.bboxes(doc)
        print("B g3 bbox (our user units):", [round(v, 1) for v in b["g3"]])
        # C: a 100 x 100 viewBox in a 200 x 100 px viewport; and preserveAspectRatio none
        for par in (None, "none"):
            svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" viewBox="0 0 100 100"'
                   + (f' preserveAspectRatio="{par}"' if par else "")
                   + '><rect id="r" x="0" y="0" width="100" height="100" fill="#c00"/></svg>').encode()
            d = Document.from_bytes(svg)
            print(f"C pAR={par}: page px", page_px(eng, svg, f"c_{par}"), "rect bbox", [round(v, 1) for v in eng.bboxes(d)["r"]],
                  "px/uu", d.px_per_user_unit)
        # D -----------------------------------------------------------------------------------------
        flow = (SRC / "flowsample.svg").read_bytes()
        d = Document.from_bytes(flow)
        print("D flowsample root:", {k: d.root.get(k) for k in ("width", "height", "viewBox")},
              "-> viewbox", [round(v, 2) for v in d.viewbox], "px/uu", d.px_per_user_unit, "unit", d.unit,
              "page px", page_px(eng, flow, "flow"))
        print("D outline:", d.outline())
        # E -----------------------------------------------------------------------------------------
        lib = Document.open(SRC / "MapSymbolsNPS.svg")
        use510 = lib._find("use510")
        print("E opened: use510 ->", use510.get("{http://www.w3.org/1999/xlink}href") if use510 is not None else None)
        host = Document.create(100, 100, "mm")
        host.add({"type": "rect", "id": "x", "x": 0, "y": 0, "width": 5, "height": 5})
        from inksmcp import files
        files.import_svg(host, SRC / "MapSymbolsNPS.svg", (0, 0), None, None, host.layer("Layer 1"), "lib")
        u = host._find("use510")
        print("E imported: use510 ->", u.get("{http://www.w3.org/1999/xlink}href") if u is not None else None)
        print("E library root style:", lib.root.get("style"))


if __name__ == "__main__":
    main()


def rendering_unchanged():
    """F. Does normalise() keep the rendering? Export the page before and after, compare pixels."""
    import hashlib
    with InkscapeShell() as sh:
        eng = Engine(sh)
        cases = {"tiger": gzip.decompress((SRC / "tiger.svgz").read_bytes()),
                 "lib": (SRC / "MapSymbolsNPS.svg").read_bytes(),
                 "meet": b'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" viewBox="10 0 100 100">'
                         b'<rect x="10" y="0" width="100" height="100" fill="#c00"/><circle cx="60" cy="50" r="20"/></svg>',
                 "none": b'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" viewBox="0 0 100 100" '
                         b'preserveAspectRatio="none" stroke="#00f"><rect x="0" y="0" width="100" height="100" '
                         b'fill="#c00"/><circle cx="50" cy="50" r="20" fill="none"/></svg>'}
        for name, data in cases.items():
            before = eng.export(Document.from_bytes(data), OUT / f"e30f_{name}_before.png", "png", area="page", dpi=96)
            d = Document.from_bytes(data)
            notes = d.normalise()
            after = eng.export(d, OUT / f"e30f_{name}_after.png", "png", area="page", dpi=96)
            same = hashlib.sha1(before.read_bytes()).digest() == hashlib.sha1(after.read_bytes()).digest()
            print(f"F {name}: identical PNG={same}, sizes {png_size(before)} {png_size(after)}; notes: {len(notes)}")


if __name__ == "__main__" and "F" in __import__("sys").argv:
    rendering_unchanged()
