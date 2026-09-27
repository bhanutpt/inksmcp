"""E13: Groundwork for `z_order`.

A. selection-raise/lower vs selection-stack-up/down: one sibling step, or "past the next overlapping object"?
B. selection-top/bottom inside a layer: stays within the layer?
C. Multiple selected ids: is their relative order kept?

Run: uv run python experiments/e13_z_order.py
"""
from inksmcp.document import Document
from inksmcp.engine import Engine

eng = Engine()


def make():
    doc = Document.create(200, 100)
    # a overlaps c only; b and d are far away
    doc.add({"type": "rect", "id": "a", "x": 10, "y": 10, "width": 30, "height": 30, "layer": "L"})
    doc.add({"type": "rect", "id": "b", "x": 150, "y": 60, "width": 10, "height": 10, "layer": "L"})
    doc.add({"type": "rect", "id": "c", "x": 20, "y": 20, "width": 30, "height": 30, "layer": "L"})
    doc.add({"type": "rect", "id": "d", "x": 170, "y": 60, "width": 10, "height": 10, "layer": "L"})
    doc.add({"type": "rect", "id": "z", "x": 0, "y": 0, "width": 5, "height": 5, "layer": "Other"})
    return doc


def order(doc):
    return {lay.get("{http://www.inkscape.org/namespaces/inkscape}label"): [c.get("id") for c in lay]
            for lay in doc.layers()}


print("start:", order(make()))
for action, sel in [("selection-raise", ["a"]), ("selection-stack-up", ["a"]), ("selection-lower", ["d"]),
                    ("selection-stack-down", ["d"]), ("selection-top", ["a"]), ("selection-bottom", ["d"]),
                    ("selection-top", ["a", "b"]), ("selection-raise", ["a", "b"]), ("selection-stack-up", ["a", "b"])]:
    doc = make()
    msgs = eng.run_actions(doc, [action], select=sel)
    print(f"{action:22s} {sel!s:12s} -> {order(doc)} {msgs}")
eng.close()
