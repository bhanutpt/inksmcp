"""E08: Rebuild the E06 diagram using `align` — labels are dropped anywhere, no baseline maths.
Compare agent effort with E06.

Run: uv run python experiments/e08_diagram_with_align.py
"""
import asyncio
import base64
import json
import time
from pathlib import Path

from mcp import Client, StdioServerParameters

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)


async def main():
    params = StdioServerParameters(command="uv", args=["run", "inksmcp"], cwd=str(Path(__file__).parents[1]))
    async with Client(params) as c:
        async def call(name, **args):
            t = time.perf_counter()
            r = await c.call_tool(name, args)
            txt = next((x.text for x in r.content if x.type == "text"), "")
            print(f"{name:14s} {(time.perf_counter() - t) * 1000:6.0f} ms err={r.is_error} {txt[:150]}")
            return r

        await call("document_create", width=240, height=120, unit="mm", background="#ffffff")
        names = [("client", "Client"), ("server", "inksmcp"), ("ink", "Inkscape")]
        els = []
        for i, (id_, label) in enumerate(names):
            els += [
                {"type": "rect", "id": id_, "x": i * 75, "y": 0, "width": 50, "height": 30, "rx": 4,
                 "fill": "#eef3fb", "stroke": "#2f5d9e", "stroke_width": 0.8, "layer": "Boxes"},
                {"type": "text", "id": f"{id_}_label", "x": 0, "y": 0, "text": label, "font_size": 6,
                 "font_family": "sans-serif", "layer": "Labels"},
            ]
        els.append({"type": "text", "id": "title", "x": 0, "y": 0, "text": "MCP → Inkscape (aligned)",
                    "font_size": 9, "font_weight": "bold", "font_family": "sans-serif", "layer": "Labels"})
        await call("add_elements", elements=els)
        ops = [{"ids": ["client", "server", "ink"], "to": "page", "horizontal": "center", "vertical": "middle",
                "as_group": True}]
        ops += [{"ids": [f"{i}_label"], "to": i, "horizontal": "center", "vertical": "middle"} for i, _ in names]
        ops += [{"ids": ["title"], "to": "page", "horizontal": "center", "vertical": "top", "margin": 20}]
        r = await call("align", operations=ops, preview=True)
        img = next(x for x in r.content if x.type == "image")
        (OUT / "e08_preview.png").write_bytes(base64.b64decode(img.data))
        await call("document_save", path=str(OUT / "e08.svg"))
    ys = [l for l in (OUT / "e08.svg").read_text(encoding="utf-8").splitlines() if l.strip().startswith(("y=", "x="))]
    print("text/rect coordinates written:", ys[:12])


asyncio.run(main())
