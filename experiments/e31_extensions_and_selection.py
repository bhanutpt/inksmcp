"""E31: Do extension actions in shell mode honour the selection? (field report 12, N3: desaturate turned the
whole car grey although `select` named 33 paths.)

Two red rects, select one, run an extension action, see which changed. Compare with a built-in action
(object-flip-horizontal) that is known to act on the selection.

Run: uv run --no-sync python experiments/e31_extensions_and_selection.py
"""
from inksmcp.document import Document, parse_style
from inksmcp.engine import Engine
from inksmcp.inkscape import InkscapeShell


def main():
    with InkscapeShell() as sh:
        eng = Engine(sh)
        for action in ("org.inkscape.color.desaturate", "org.inkscape.color.negative", "object-flip-horizontal"):
            doc = Document.create(100, 50, "mm")
            doc.add({"type": "rect", "id": "a", "x": 5, "y": 5, "width": 20, "height": 20, "fill": "#cc2222"})
            doc.add({"type": "rect", "id": "b", "x": 50, "y": 5, "width": 30, "height": 20, "fill": "#cc2222",
                     "transform": "rotate(10 65 15)"})
            before = {i: (parse_style(doc.get(i).get("style")).get("fill"), doc.get(i).get("transform")) for i in "ab"}
            try:
                msgs = eng.run_actions(doc, [action], select=["a"])
            except Exception as e:  # noqa: BLE001
                print(f"{action}: error {e}")
                continue
            after = {i: (parse_style(doc.get(i).get("style")).get("fill"), doc.get(i).get("transform")) for i in "ab"}
            changed = [i for i in "ab" if before[i] != after[i]]
            print(f"{action}: changed {changed} (selected ['a']); {after}; messages {len(msgs)}")


if __name__ == "__main__":
    main()
