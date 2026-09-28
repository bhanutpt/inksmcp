"""E22: Which id survives a path operation? (field report 7: combine kept the top id, docs said bottom)
Questions:
  A. union / combine / intersection / exclusion / difference: which id and style survive, for 3 objects?
  B. Does the selection order (select-by-id a,b,c vs c,b,a) change the survivor?
  C. Objects in different groups/layers: where does the result go?

Run: uv run python experiments/e22_path_ids.py
"""
from inksmcp.document import Document
from inksmcp.engine import Engine

eng = Engine()


def trial(op: str, order: list[str], layers: bool = False, n: int = 3) -> None:
    doc = Document.create(100, 60, "mm")
    names = ["o0", "o1", "o2"][:n]
    for k, name in enumerate(names):  # o0 bottom ... o2 top, overlapping
        spec = {"type": "rect", "id": name, "x": 10 + 12 * k, "y": 10 + 4 * k, "width": 30, "height": 20,
                "fill": ["#c00", "#0a0", "#00c"][k]}
        if layers:
            spec["layer"] = f"L{k}"
        doc.add(spec)
    before = set(doc.ids())
    eng.run_actions(doc, [op], select=[o for o in order if o in names])
    after = doc.ids()
    survivors = [i for i in names if i in after]
    created = [i for i in after if i not in before]
    fills = {i: doc.get(i).get("style") for i in survivors + created}
    where = {i: doc.get(i).getparent().get("id") for i in survivors + created}
    print(f"{op:18} order={','.join(order):9} layers={layers!s:5} survivors={survivors} created={created} "
          f"parent={where} style={fills}")


for op in ["path-union", "path-combine", "path-intersection", "path-exclusion"]:
    trial(op, ["o0", "o1", "o2"])
    trial(op, ["o2", "o1", "o0"])
for op in ["path-difference", "path-division", "path-cut"]:
    trial(op, ["o0", "o1"], n=2)
    trial(op, ["o1", "o0"], n=2)
print("-- C: objects in separate layers")
for op in ["path-union", "path-combine"]:
    trial(op, ["o0", "o1", "o2"], layers=True)
eng.close()
