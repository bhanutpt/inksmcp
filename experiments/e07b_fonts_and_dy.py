"""E07b: Do generic families (serif/sans-serif) resolve to different fonts? Direction of transform-translate dy?

Run: uv run python experiments/e07b_fonts_and_dy.py
"""
from pathlib import Path

from inksmcp.document import Document
from inksmcp.engine import Engine

OUT = Path(__file__).parent / "out"
eng = Engine()
doc = Document.create(300, 100, "px")
fams = ["sans-serif", "serif", "monospace", "Arial", "Times New Roman", "Georgia", "Segoe UI", "NoSuchFont123"]
for i, fam in enumerate(fams):
    doc.add({"type": "text", "id": f"f{i}", "x": 10, "y": 50, "text": "Hamburg", "font_size": 20, "font_family": fam})
b = eng.bboxes(doc)
for i, fam in enumerate(fams):
    x, y, w, h = b[f"f{i}"]
    print(f"   {fam:16s} width={w:6.2f} cap/above={(50 - y) / 20:.3f}em")

doc = Document.create(100, 100, "mm")
doc.add({"type": "rect", "id": "r", "x": 10, "y": 10, "width": 10, "height": 10})
eng.run_actions(doc, ["transform-translate:0,37.795276"], select=["r"])  # 10 mm in px
print("   rect y after translate 0,+10mm:", doc.get("r").get("y"), doc.get("r").get("transform"))
eng.close()
