"""E05: Are export-* options sticky across commands / file-open in --shell? Does export-width stick?

Run: uv run python experiments/e05_sticky_export.py
"""
import struct
from pathlib import Path

from inksmcp.inkscape import InkscapeShell

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
src = OUT / "e05.svg"
src.write_text("""<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" viewBox="0 0 200 100">
<rect id="a" x="10" y="10" width="40" height="40" style="fill:red"/>
<rect id="b" x="100" y="20" width="80" height="60" style="fill:blue"/></svg>""", encoding="utf-8")


def png_size(p: Path):
    d = p.read_bytes()[16:24]
    return struct.unpack(">II", d)


with InkscapeShell() as sh:
    sh.run(f"file-open:{src}")
    sh.run(f"export-filename:{OUT/'e05_1.png'};export-type:png;export-width:400;export-do")
    print("1 width=400:", png_size(OUT / "e05_1.png"))
    sh.run(f"export-filename:{OUT/'e05_2.png'};export-do")
    print("2 no width (sticky?):", png_size(OUT / "e05_2.png"))
    sh.run(f"export-filename:{OUT/'e05_3.png'};export-id:b;export-id-only;export-width:0;export-do")
    print("3 export-id b, width 0:", png_size(OUT / "e05_3.png"))
    sh.run(f"export-filename:{OUT/'e05_4.png'};export-area-page;export-do")
    print("4 area-page after id:", png_size(OUT / "e05_4.png"))
    sh.run("file-close")
    sh.run(f"file-open:{src}")
    sh.run(f"export-filename:{OUT/'e05_5.png'};export-do")
    print("5 after reopen:", png_size(OUT / "e05_5.png"))
    r = sh.run(f"export-filename:{OUT/'e05_6.svg'};export-type:svg;export-do", check=False)
    print("6 svg export head:", (OUT / "e05_6.svg").read_bytes()[:60], r.messages)
    # timing of an open+query+close round-trip
    import time
    t = time.perf_counter()
    for _ in range(10):
        sh.run(f"file-open:{src}")
        sh.run("query-all")
        sh.run("file-close")
    print(f"open+query+close avg: {(time.perf_counter()-t)*100:.1f} ms")
