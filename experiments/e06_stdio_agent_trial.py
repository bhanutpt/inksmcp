"""E06: Real usage — launch the server over stdio (like Claude Desktop/Code would) and build a
small architecture diagram the way an agent would, measuring calls and latency.

Run: uv run python experiments/e06_stdio_agent_trial.py
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
    calls = 0

    async with Client(params) as c:
        async def call(name, **args):
            nonlocal calls
            calls += 1
            t = time.perf_counter()
            r = await c.call_tool(name, args)
            dt = (time.perf_counter() - t) * 1000
            txt = next((x.text for x in r.content if x.type == "text"), "")
            print(f"{name:16s} {dt:7.0f} ms  err={r.is_error}  {txt[:160]}")
            return r

        tools = (await c.list_tools()).tools
        desc_chars = sum(len(t.description or "") + len(json.dumps(t.input_schema)) for t in tools)
        print(f"{len(tools)} tools, ~{desc_chars} chars of tool schema")

        await call("inkscape_info")
        await call("document_create", width=240, height=120, unit="mm", background="#ffffff")
        boxes = [("client", "Client", 20), ("server", "inksmcp", 95), ("ink", "Inkscape", 170)]
        els = []
        for id_, label, x in boxes:
            els += [
                {"type": "rect", "id": id_, "x": x, "y": 45, "width": 50, "height": 30, "rx": 4,
                 "fill": "#eef3fb", "stroke": "#2f5d9e", "stroke_width": 0.8, "layer": "Boxes"},
                {"type": "text", "id": f"{id_}_label", "x": x + 25, "y": 62, "text": label, "font_size": 6,
                 "text_anchor": "middle", "font_family": "sans-serif", "layer": "Labels"},
            ]
        els += [
            {"type": "line", "id": "a1", "x1": 70, "y1": 60, "x2": 95, "y2": 60, "stroke_width": 0.8, "layer": "Arrows"},
            {"type": "line", "id": "a2", "x1": 145, "y1": 60, "x2": 170, "y2": 60, "stroke_width": 0.8, "layer": "Arrows"},
            {"type": "text", "id": "title", "x": 120, "y": 25, "text": "MCP → Inkscape", "font_size": 9,
             "font_weight": "bold", "text_anchor": "middle", "font_family": "sans-serif", "layer": "Labels"},
        ]
        r = await call("add_elements", elements=els, preview=True)
        img = next(x for x in r.content if x.type == "image")
        (OUT / "e06_preview.png").write_bytes(base64.b64decode(img.data))
        r = await call("inspect")
        outline = json.loads(r.content[0].text)
        print("inspect payload chars:", len(r.content[0].text))
        labels = [ch for n in outline["outline"] if n.get("label") == "Labels" for ch in n["children"]]
        for l in labels:
            print("  ", l["id"], l["bbox"])
        await call("export", path=str(OUT / "e06_diagram.pdf"))
        await call("export", path=str(OUT / "e06_diagram.png"), dpi=150)
        await call("document_save", path=str(OUT / "e06_diagram.svg"))
        r = await call("update_elements", updates=[{"id": "nope", "fill": "red"}])
    print(f"total tool calls: {calls}")


asyncio.run(main())
