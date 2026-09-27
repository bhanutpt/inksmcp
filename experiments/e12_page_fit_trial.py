"""E12: Real usage — build the E10 flowchart on a page that is too small, get the off-page warning,
fix it with a single page_fit, and check the saved SVG for coordinate noise (F14).

Run: uv run python experiments/e12_page_fit_trial.py
"""
import asyncio
import base64
import re
from pathlib import Path

from mcp import Client, StdioServerParameters

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)


async def main():
    params = StdioServerParameters(command="uv", args=["run", "inksmcp"], cwd=str(Path(__file__).parents[1]))
    async with Client(params) as c:
        async def call(name, **args):
            r = await c.call_tool(name, args)
            txt = next((x.text for x in r.content if x.type == "text"), "")
            print(f"{name:12s} err={r.is_error} {txt[:230]}")
            return r

        await call("document_create", width=160, height=190, unit="mm", background="#ffffff")
        box = {"type": "rect", "width": 50, "height": 16, "rx": 3, "fill": "#eef3fb", "stroke": "#2f5d9e",
               "stroke_width": 0.5}
        txt = {"type": "text", "font_size": 5, "font_family": "sans-serif"}
        names = {"start": "Request", "parse": "Parse spec", "render": "Render", "done": "Return image",
                 "error": "Report error"}
        els = [dict(box, id=i) for i in names] + [dict(txt, id=f"{i}_t", text=t) for i, t in names.items()]
        els += [{"type": "polygon", "id": "valid", "points": [[25, 0], [50, 12], [25, 24], [0, 12]],
                 "fill": "#fff7e0", "stroke": "#b58900", "stroke_width": 0.5}, dict(txt, id="valid_t", text="Valid?")]
        await call("add_elements", elements=els)
        await call("align", operations=[{"ids": [f"{i}_t"], "to": i, "horizontal": "center", "vertical": "middle"}
                                        for i in [*names, "valid"]])
        await call("layout", items=[[i, f"{i}_t"] for i in ["start", "parse", "valid", "render", "done"]],
                   direction="column", gap=14, to="page", horizontal="center", vertical="top", margin=12)
        await call("layout", items=[["valid", "valid_t"], ["error", "error_t"]], direction="row", gap=20)
        await call("connect", connections=[
            {"from": "start", "to": "parse"}, {"from": "parse", "to": "valid"},
            {"from": "valid", "to": "render", "label": "yes"}, {"from": "valid", "to": "error", "label": "no"},
            {"from": "render", "to": "done"}, {"from": "error", "to": "done", "routing": "elbow"}])
        r = await call("page_fit", margin=10, preview=True)
        (OUT / "e12_fitted.png").write_bytes(base64.b64decode(r.content[1].data))
        await call("document_save", path=str(OUT / "e12.svg"))
    svg = (OUT / "e12.svg").read_text(encoding="utf-8")
    noisy = re.findall(r'(?:x|y|transform)="[^"]*\d\.\d{4,}[^"]*"', svg)
    print("attributes with >3 decimals:", noisy[:8], len(noisy))


asyncio.run(main())
