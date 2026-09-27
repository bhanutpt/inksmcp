"""E16: Redo the field test (A4 log-log 3x5 cycles) with the new `grid` tool; zoom with region.
Compare with docs/field-reports/2026-09-27-log-graph-a4.md (14 calls + external coordinate script).

Run: uv run python experiments/e16_log_paper_with_grid.py
"""
import asyncio
import base64
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
            txt = next((x.text for x in r.content if x.type == "text"), "")
            print(f"{name:14s} {(time.perf_counter() - t) * 1000:6.0f} ms err={r.is_error} chars={len(txt)} {txt[:150]}")
            return r

        await call("document_create", width=210, height=297, unit="mm", background="#ffffff")
        await call("grid", rect=[24, 15, 171, 260], x={"scale": "log", "cycles": 3}, y={"scale": "log", "cycles": 5},
                   color="#2a8a4a", labels={"sides": ["left", "bottom"]})
        await call("add_elements", elements=[{"type": "text", "id": "caption", "x": 195, "y": 287,
                                              "text": "Log-log  3 x 5 cycles", "font_size": 3,
                                              "fill": "#2a8a4a", "text_anchor": "end",
                                              "vertical_anchor": "middle"}])
        r = await call("render_preview", region=[10, 250, 45, 35], max_size=900)
        (OUT / "e16_corner.png").write_bytes(base64.b64decode(r.content[0].data))
        await call("inspect", bbox=False)
        await call("export", path=str(OUT / "e16_log_a4.png"), dpi=300, background="#ffffff")
    print("tool calls:", calls)


asyncio.run(main())
