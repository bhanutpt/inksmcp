"""E14: Scale check — ~350 elements in one add_elements call over stdio, inspect payload size,
A4 export at 300 dpi. (Prep for the log-paper field test.)

Run: uv run python experiments/e14_scale_many_elements.py
"""
import asyncio
import math
import struct
import time
from pathlib import Path

from mcp import Client, StdioServerParameters

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)


def ticks():
    vals = [1 + i * 0.1 for i in range(10)] + [2 + i * 0.2 for i in range(15)] + [5 + i * 0.5 for i in range(10)]
    return [math.log10(v) for v in vals]


async def main():
    params = StdioServerParameters(command="uv", args=["run", "inksmcp"], cwd=str(Path(__file__).parents[1]))
    async with Client(params) as c:
        async def call(name, **args):
            t = time.perf_counter()
            r = await c.call_tool(name, args)
            txt = next((x.text for x in r.content if x.type == "text"), "")
            print(f"{name:14s} {(time.perf_counter() - t) * 1000:7.0f} ms err={r.is_error} chars={len(txt)} {txt[:100]}")
            return r

        await call("document_create", width=210, height=297, unit="mm", background="#ffffff")
        x0, y0, w, h = 15, 15, 180, 267
        els = []
        for d in range(3):
            for f in ticks():
                x = x0 + (d + f) / 3 * w
                els.append({"type": "line", "x1": x, "y1": y0, "x2": x, "y2": y0 + h, "stroke": "#2a8a4a",
                            "stroke_width": 0.3 if f == 0 else 0.1, "layer": "Grid"})
        for d in range(5):
            for f in ticks():
                y = y0 + h - (d + f) / 5 * h
                els.append({"type": "line", "x1": x0, "y1": y, "x2": x0 + w, "y2": y, "stroke": "#2a8a4a",
                            "stroke_width": 0.3 if f == 0 else 0.1, "layer": "Grid"})
        els += [{"type": "text", "x": x0 - 2, "y": y0 + h - k / 45 * h, "text": str(k % 9 + 1), "font_size": 2.5,
                 "fill": "#2a8a4a", "text_anchor": "end", "layer": "Labels"} for k in range(45)]
        print("elements:", len(els))
        await call("add_elements", elements=els)
        await call("inspect")
        await call("inspect", bbox=False)
        await call("export", path=str(OUT / "e14_a4_300dpi.png"), dpi=300, background="#ffffff")
        r = await call("render_preview", max_size=800)
    data = (OUT / "e14_a4_300dpi.png").read_bytes()
    print("png size px:", struct.unpack(">II", data[16:24]), "bytes:", len(data))


asyncio.run(main())
