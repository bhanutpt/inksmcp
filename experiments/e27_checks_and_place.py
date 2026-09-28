"""E27: Real usage for step 2 (automatic overlap warnings, stored `place`, layout anchors), replaying the
round-2 situations through the MCP tools:
  A. Tamil card (report 4): sound label `place`d below the letter's measured glyphs; the letter grows later
     and the label follows; no hand-picked baselines.
  B. Map labels (report 8 / E26): do the warnings name the real collisions, and only those?
  C. Flowchart (report 9): labels inside boxes and connectors between them: no false warnings; a label
     pushed onto a box edge is reported.
  D. Datasheet (report 10): two plots whose tick labels differ in width, laid out by their frames.
  E. Timing: what the check costs per call.

Run: uv run python experiments/e27_checks_and_place.py
"""
import asyncio
import json
import time
from pathlib import Path

from mcp import Client

from inksmcp import server

OUT = Path(__file__).parent / "out"


async def main():
    async with Client(server.mcp) as c:
        async def call(name, **args):
            t = time.perf_counter()
            r = await c.call_tool(name, args)
            assert not r.is_error, r.content[0].text
            out = json.loads(r.content[0].text)
            out["_ms"] = round((time.perf_counter() - t) * 1000)
            return out

        # A ------------------------------------------------------------------------------------------
        await call("document_create", width=120, height=80, unit="mm", background="#fffaf0")
        letters = [{"l": "அ", "s": "a"}, {"l": "இ", "s": "i"}, {"l": "ஔ", "s": "au"}]
        r = await call("repeat", rows=letters, step=[40, 0], template=[
            {"type": "group", "id": "card"},
            {"type": "rect", "id": "box", "parent": "card", "x": 2, "y": 5, "width": 36, "height": 50,
             "fill": "#fff", "stroke": "#7a1f2b", "stroke_width": 0.4},
            {"type": "text", "id": "letter", "parent": "card", "x": 20, "y": 30, "text": "{l}", "font_size": 16,
             "font_family": "Nirmala UI", "text_anchor": "middle"},
            {"type": "text", "id": "sound", "parent": "card", "x": 20, "y": 0, "text": "{s}", "font_size": 5,
             "text_anchor": "middle", "place": {"below": "letter", "gap": 1.5}}])
        print("A stamp:", r.get("placed"), r.get("warnings"))
        insp = await call("inspect", layer="card-3", max_children=10)
        print("A inspect card-3:", [(n["id"], n.get("bbox")) for n in insp["outline"]])
        r = await call("update_elements", updates=[{"id": "letter-1", "font_size": 22}])
        print("A grow letter-1 ->", r.get("placed"), r.get("warnings"))

        # B ------------------------------------------------------------------------------------------
        await call("document_create", width=200, height=120, unit="mm")
        await call("add_elements", elements=[
            {"type": "polyline", "id": "road", "points": [[10, 60], [190, 60]], "stroke": "#b0a080", "stroke_width": 1}])
        towns = [{"name": "Alpha", "x": 20, "y": 30}, {"name": "Beta", "x": 30, "y": 31},  # Alpha/Beta collide
                 {"name": "Gamma", "x": 80, "y": 61},                                     # sits on the road, no halo
                 {"name": "Delta", "x": 120, "y": 61, "h": "#fff"},                       # on the road with halo: fine
                 {"name": "Eps", "x": 160, "y": 90}]
        r = await call("repeat", rows=[{**t, "h": t.get("h", "none")} for t in towns], step=[0, 0], template=[
            {"type": "text", "id": "t", "x": "{x}", "y": "{y}", "text": "{name}", "font_size": 5, "halo": "{h}"}])
        print("B warnings:", r.get("warnings"), f"({r['_ms']} ms)")

        # C ------------------------------------------------------------------------------------------
        await call("document_create", width=200, height=100, unit="mm")
        await call("add_elements", elements=[
            {"type": "rect", "id": f"n{k}", "x": 10 + 60 * k, "y": 40, "width": 40, "height": 16, "rx": 2,
             "fill": "#eef", "stroke": "#336", "stroke_width": 0.4} for k in range(3)] + [
            {"type": "text", "id": f"n{k}_t", "x": 30 + 60 * k, "y": 50, "text": f"Step {k + 1}", "font_size": 4,
             "text_anchor": "middle"} for k in range(3)])
        r = await call("connect", connections=[{"from": "n0", "to": "n1", "label": "ok"},
                                               {"from": "n1", "to": "n2", "label": "Yes, deploy", "label_offset": 2}])
        print("C connect warnings:", r.get("warnings"))
        r = await call("update_elements", updates=[{"id": "n2_t", "x": 170}])
        print("C label pushed onto an edge:", r.get("warnings"))

        # D ------------------------------------------------------------------------------------------
        await call("document_create", width=210, height=120, unit="mm")
        await call("grid", rect=[20, 20, 70, 50], id_prefix="f1", layer_prefix="F1",
                   x={"scale": "linear", "major": 14, "minor": 7, "label_start": 0, "label_step": 1},
                   y={"scale": "linear", "major": 10, "label_start": 0, "label_step": 1},
                   labels={"sides": ["left", "bottom"]})
        await call("grid", rect=[20, 20, 70, 50], id_prefix="f2", layer_prefix="F2",
                   x={"scale": "linear", "major": 14, "minor": 7, "label_start": 0, "label_step": 1},
                   y={"scale": "linear", "major": 10, "label_start": 0.001, "label_step": 1000.25},
                   labels={"sides": ["left", "bottom"]})
        insp = await call("inspect", bbox=False)
        layers = {n["label"]: n["id"] for n in insp["outline"] if n["type"] == "layer"}
        f1 = [v for k, v in layers.items() if k.startswith("F1")]
        f2 = [v for k, v in layers.items() if k.startswith("F2")]
        r = await call("layout", items=[{"ids": f1, "anchor": "f1-border"}, {"ids": f2, "anchor": "f2-border"}],
                       direction="row", gap=25, at=[25, 30])
        b = (await call("inspect"))
        boxes = {}

        def walk(nodes):
            for n in nodes:
                if n.get("bbox"):
                    boxes[n["id"]] = n["bbox"]
                walk(n.get("children", []))
        walk(b["outline"])
        print("D frames:", boxes["f1-border"], boxes["f2-border"], "(same y, x gap 25 between frames)")
        await call("export", path=str(OUT / "e27_datasheet.png"), dpi=60)


asyncio.run(main())
