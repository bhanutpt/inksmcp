"""E29: False-positive overlap warnings (comic page 2 report, 2026-09-28).

Question: the report saw 15 warnings like "text 'b1_t' crosses the edge of 'stripe-9'" for texts that sit
on their own opaque balloon / caption box above a striped wallpaper. Which warnings does the check give on
the finished pages when every text counts as touched, and which of them are hidden under an opaque shape
painted above the other element?

Run: uv run python experiments/e29_occluded_overlaps.py
"""
from collections import Counter
from pathlib import Path

from inksmcp.document import Document
from inksmcp.engine import Engine
from inksmcp.inkscape import InkscapeShell

OUT = Path(__file__).parents[1] / "out"
PAGES = ["comic-last-cookie-p2.svg", "comic-nutmeg-panel.svg", "comic-last-cookie.svg",
         "flowchart-pr-to-production-a4.svg", "periodic-table-a3.svg", "route-map-blr-chennai-a3.svg",
         "tamil-alphabet-a3.svg", "floor-plan-2bhk-a4.svg", "datasheet-ldo-317-a4.svg", "heat-pump-poster.svg"]


def main():
    with InkscapeShell() as sh:
        eng = Engine(sh)
        for name in PAGES:
            p = OUT / name
            if not p.exists():
                continue
            doc = Document.open(p)
            texts = {e.get("id") for e in doc.root.iter() if isinstance(e.tag, str)
                     and e.tag.endswith("}text") and e.get("id")}
            checks_mod = __import__("inksmcp.checks", fromlist=["MAX_WARNINGS"])
            checks_mod.MAX_WARNINGS = 10_000
            w = eng.check_layout(doc, texts)
            kinds = Counter(x.split(" ")[2] if x.startswith("text") else "stack" for x in w)
            print(f"\n== {name}: {len(texts)} texts, {len(w)} warnings {dict(kinds)}")
            for x in w[:25]:
                print("  ", x)


if __name__ == "__main__":
    main()
