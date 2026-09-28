"""E26: Real usage for step 1 (files in). Field report 8 could not pass 51 kB of map geometry through the
tools. Stand-in: a script writes ~50 kB of "roads" into an SVG and 40 towns into a CSV; the agent then
builds an A3 map with a photo inset through the MCP tools only. Measures calls and request/response chars.

Run: uv run python experiments/e26_files_in_trial.py
"""
import asyncio
import json
import math
import random
from pathlib import Path

from mcp import Client

from inksmcp import server
from inksmcp.document import Document
from inksmcp.engine import Engine

OUT = Path(__file__).parent / "out" / "e26"
OUT.mkdir(parents=True, exist_ok=True)
random.seed(8)

# -- what the agent's own script would produce ------------------------------------------------------
geo = Document.create(4000, 2800, "px")  # "projected" map units
for k in range(60):
    x, y, pts = random.uniform(0, 4000), random.uniform(0, 2800), []
    for _ in range(60):
        x += random.uniform(-60, 60)
        y += random.uniform(-60, 60)
        pts.append([round(x, 1), round(y, 1)])
    geo.add({"type": "polyline", "points": pts, "stroke": "#b0a080", "stroke_width": 4,
             "layer": "Roads major" if k < 12 else "Roads minor"})
geo.save(OUT / "roads.svg")
towns = OUT / "towns.csv"
towns.write_text("name,x,y,size\n" + "".join(
    f"Town {k},{random.uniform(30, 390):.1f},{random.uniform(40, 270):.1f},{random.choice([3, 4, 5])}\n"
    for k in range(40)), encoding="utf-8")
eng = Engine()
photo = Document.create(400, 300, "px")
photo.add({"type": "rect", "x": 0, "y": 0, "width": 400, "height": 300, "fill": "#6a8"})
photo.add({"type": "circle", "cx": 200, "cy": 150, "r": 90, "fill": "#fd4"})
eng.export(photo, OUT / "photo.png", "png")
eng.close()
print(f"roads.svg {(OUT / 'roads.svg').stat().st_size / 1024:.0f} kB, towns.csv 40 rows")

# -- the agent -------------------------------------------------------------------------------------------
stats = {"calls": 0, "req": 0, "resp": 0}


async def main():
    async with Client(server.mcp) as c:
        async def call(name, **args):
            stats["calls"] += 1
            stats["req"] += len(json.dumps(args))
            r = await c.call_tool(name, args)
            body = r.content[0].text
            stats["resp"] += len(body)
            assert not r.is_error, body
            return json.loads(body)

        await call("document_create", width=420, height=297, unit="mm", background="#f7f3ea")
        await call("add_elements", elements=[
            {"type": "rect", "id": "frame", "x": 20, "y": 30, "width": 380, "height": 250, "fill": "none",
             "stroke": "#333", "stroke_width": 0.6, "layer": "Frame"},
            {"type": "text", "id": "title", "x": 20, "y": 22, "text": "Roads of the Stand-in District",
             "font_size": 9, "font_weight": "bold", "layer": "Frame"}])
        r = await call("import_file", path=str(OUT / "roads.svg"), at=[10, 20], width=400, layer="Map")
        print("import:", {k: r[k] for k in ("id", "elements", "size", "layers_as_groups", "bbox")})
        await call("update_elements", updates=[{"id": r["id"], "clip": "frame"}])
        r = await call("repeat", rows_path=str(towns), step=[0, 0], layer="Towns", template=[
            {"type": "circle", "id": "dot", "cx": "{x}", "cy": "{y}", "r": 1.2, "fill": "#a22"},
            {"type": "text", "id": "name", "x": "{x}", "y": "{y}", "text": "{name}", "font_size": "{size}",
             "halo": "#f7f3ea"}])
        print("towns:", r["groups"], r["ids"]["name"])
        r = await call("import_file", path=str(OUT / "photo.png"), at=[300, 200], width=80, height=60,
                       object_fit="cover", layer="Inset")
        await call("export", path=str(OUT / "e26_map.png"), dpi=60)
    print(f"{stats['calls']} calls, request {stats['req']:,} chars, response {stats['resp']:,} chars")


asyncio.run(main())
