"""E05b: isolate export-id behaviour and whether file-open resets export options.

Run: uv run python experiments/e05b_export_id.py
"""
import struct
from pathlib import Path

from inksmcp.inkscape import InkscapeShell

OUT = Path(__file__).parent / "out"
src = OUT / "e05.svg"  # from e05: a=40x40 at 10,10 ; b=80x60 at 100,20 ; page 200x100


def size(name):
    return struct.unpack(">II", (OUT / name).read_bytes()[16:24])


def fresh(sh):
    sh.run("file-close", check=False)
    sh.run(f"file-open:{src}")


cases = {
    "id_plain": "export-id:b;export-do",
    "id_only": "export-id:b;export-id-only;export-do",
    "id_area_drawing": "export-id:b;export-area-drawing;export-do",
    "select_then_export": "select-by-id:b;export-area-drawing;export-do",
    "drawing": "export-area-drawing;export-do",
    "area_explicit": "export-area:100:20:180:80;export-do",
}
with InkscapeShell() as sh:
    for name, acts in cases.items():
        fresh(sh)
        r = sh.run(f"export-filename:{OUT / (name + '.png')};export-type:png;{acts}", check=False)
        print(f"{name:20s} -> {size(name + '.png')} {r.messages}")
    # stickiness across file-open
    fresh(sh)
    sh.run(f"export-filename:{OUT/'w1.png'};export-type:png;export-width:400;export-do")
    fresh(sh)
    sh.run(f"export-filename:{OUT/'w2.png'};export-do")
    print("width after reopen:", size("w1.png"), "->", size("w2.png"))
    fresh(sh)
    sh.run(f"export-filename:{OUT/'i1.png'};export-type:png;export-id:b;export-do")
    fresh(sh)
    sh.run(f"export-filename:{OUT/'i2.png'};export-do")
    print("id after reopen:", size("i1.png"), "->", size("i2.png"))
