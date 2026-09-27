"""E05c: can sticky export options be reset inside one shell session?

Run: uv run python experiments/e05c_export_reset.py
"""
import struct
from pathlib import Path

from inksmcp.inkscape import InkscapeShell

OUT = Path(__file__).parent / "out"
src = OUT / "e05.svg"  # page 200x100, b = 80x60


def size(name):
    return struct.unpack(">II", (OUT / name).read_bytes()[16:24])


resets = {
    "empty_id": "export-id:;export-area-page",
    "id_only_false": "export-id:;export-id-only:false;export-area-page",
    "full": "export-id:;export-id-only:false;export-area-page;export-width:0;export-height:0;export-dpi:96",
}
for name, reset in resets.items():
    with InkscapeShell() as sh:
        sh.run(f"file-open:{src}")
        sh.run(f"export-filename:{OUT/'p.png'};export-type:png;export-id:b;export-id-only;export-width:400;export-do")
        r = sh.run(f"{reset};export-filename:{OUT/(name+'.png')};export-type:png;export-do", check=False)
        print(f"{name:14s} -> {size(name + '.png')}  (want (200, 100))  {r.messages}")
