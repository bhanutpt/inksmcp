"""E28: Real usage for step 3 (grid cells, region split) and the table question (D-024).
  A. Comic page (report 5): 6 panels of mixed widths, a character clipped to its panel, a caption box —
     how many calls, how many hand-computed numbers?
  B. Periodic-table fragment (report 6): cells from a CSV with col/row, gaps and an f-block at row 9.5.
  C. Table (reports 6, 7, 8, 10): the floor plan's area statement (name | m² | ft², right-aligned numbers,
     header, total row with a rule) built from split + repeat. Is a table element still needed?

Run: uv run python experiments/e28_cells_and_tables.py
"""
import asyncio
import json
from pathlib import Path

from mcp import Client

from inksmcp import server

OUT = Path(__file__).parent / "out" / "e28"
OUT.mkdir(parents=True, exist_ok=True)
stats = {"calls": 0, "req": 0}


async def main():
    async with Client(server.mcp) as c:
        async def call(name, **args):
            stats["calls"] += 1
            stats["req"] += len(json.dumps(args))
            r = await c.call_tool(name, args)
            assert not r.is_error, r.content[0].text
            return json.loads(r.content[0].text)

        # A --------------------------------------------------------------------------------------------
        await call("document_create", width=210, height=297, unit="mm", background="#ffffff")
        r = await call("split", region="page", margin=[24, 10, 10, 10], rows=[[2, 1], [1, 1], [1, 2]], gutter=4,
                       id_prefix="panel", layer="Frames", style={"stroke": "#000", "stroke_width": 0.8})
        print("A panels:", r["rows"], r["cells"]["panel-5"])
        await call("add_elements", elements=[
            {"type": "group", "id": "cat", "transform": "translate(60,200) scale(2.2)", "clip": "panel-5",
             "layer": "Characters"},
            {"type": "circle", "id": "cat_body", "parent": "cat", "cx": 0, "cy": 0, "r": 20, "fill": "#e80"},
            {"type": "text", "id": "cap5", "x": 14, "y": 0, "text": "Meanwhile…", "font_size": 4,
             "vertical_anchor": "top", "layer": "Captions"}])
        await call("align", operations=[{"ids": ["cap5"], "to": "panel-5", "horizontal": "left", "vertical": "top",
                                         "margin": 2}])
        a_calls = stats["calls"]
        await call("export", path=str(OUT / "comic.png"), dpi=40)

        # B --------------------------------------------------------------------------------------------
        csv = OUT / "elements.csv"
        csv.write_text("sym,col,row\nH,1,1\nHe,18,1\nLi,1,2\nBe,2,2\nB,13,2\nC,14,2\nN,15,2\nO,16,2\nF,17,2\nNe,18,2\n"
                       "La,3,9.5\nCe,4,9.5\n", encoding="utf-8")
        await call("document_create", width=420, height=297, unit="mm")
        r = await call("repeat", rows_path=str(csv), cell=["col", "row"], step=[22, 24], layer="Table", template=[
            {"type": "rect", "id": "box", "x": 10, "y": 30, "width": 20, "height": 22, "fill": "#eef", "stroke": "#336",
             "stroke_width": 0.3},
            {"type": "text", "id": "s", "x": 20, "y": 44, "text": "{sym}", "font_size": 8, "text_anchor": "middle"}])
        print("B warnings:", r.get("warnings"))
        insp = await call("inspect", layer="Table", max_children=20)
        byid = {n["id"]: n for n in insp["outline"]}
        print("B He at", byid["row-2"]["bbox"][:2], "(expect x 10+17*22=384, y 30)",
              "La at", byid["row-11"]["bbox"][:2], "(expect y 30+8.5*24=234)")

        # C --------------------------------------------------------------------------------------------
        await call("document_create", width=148, height=110, unit="mm")
        table = [("Living", 18.6), ("Dining", 10.2), ("Kitchen", 8.4), ("Master bedroom", 14.1), ("Bedroom 2", 11.0),
                 ("Toilets", 7.3)]
        n0 = stats["calls"]
        r = await call("split", region=[10, 20, 128, 7], rows=[[3, 1, 1]], id_prefix="col", style={"fill": "#eee"})
        (x1, _, w1, _), (x2, _, w2, _), (x3, _, w3, _) = r["cells"].values()
        rows = [{"name": n, "m2": f"{a:.1f}", "ft2": f"{a * 10.7639:.0f}"} for n, a in table]
        total = sum(a for _, a in table)
        rows.append({"name": "TOTAL", "m2": f"{total:.1f}", "ft2": f"{total * 10.7639:.0f}"})
        await call("repeat", rows=[{"name": "Room", "m2": "m²", "ft2": "ft²"}] + rows, step=[0, 7], layer="Table",
                   id_prefix="tr", defaults={"font_size": 3.4, "vertical_anchor": "middle"}, template=[
                       {"type": "text", "id": "c1", "x": x1 + 2, "y": 23.5, "text": "{name}"},
                       {"type": "text", "id": "c2", "x": x2 + w2 - 2, "y": 23.5, "text": "{m2}", "text_anchor": "end"},
                       {"type": "text", "id": "c3", "x": x3 + w3 - 2, "y": 23.5, "text": "{ft2}", "text_anchor": "end"},
                       {"type": "line", "id": "rule", "x1": 10, "y1": 27, "x2": 138, "y2": 27, "stroke": "#999",
                        "stroke_width": 0.2}])
        await call("update_elements", updates=[{"id": "rule-7", "stroke": "#000", "stroke_width": 0.5},
                                               {"id": "c1-8", "font_weight": "bold"}, {"id": "c2-8", "font_weight": "bold"},
                                               {"id": "c3-8", "font_weight": "bold"}])
        print(f"C table: {stats['calls'] - n0} calls; numbers typed by the agent: column edges from split (3), "
              "row pitch 7, first baseline 23.5")
        await call("export", path=str(OUT / "table.png"), dpi=100)
    print(f"A: {a_calls} calls; total {stats['calls']} calls, {stats['req']:,} request chars")


asyncio.run(main())
