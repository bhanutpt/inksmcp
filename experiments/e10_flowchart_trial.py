"""E10: Real usage — a flowchart with a decision, labelled branches and elbow routing, built only
from relationships (layout / align / connect). No coordinates except shape sizes.

Run: uv run python experiments/e10_flowchart_trial.py
"""
import asyncio
import base64
import time
from pathlib import Path

from mcp import Client, StdioServerParameters

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)


async def main(width=160):
    params = StdioServerParameters(command="uv", args=["run", "inksmcp"], cwd=str(Path(__file__).parents[1]))
    calls = 0
    async with Client(params) as c:
        async def call(name, **args):
            nonlocal calls
            calls += 1
            t = time.perf_counter()
            r = await c.call_tool(name, args)
            txt = next((x.text for x in r.content if x.type == "text"), "")
            print(f"{name:14s} {(time.perf_counter() - t) * 1000:6.0f} ms err={r.is_error} {txt[:140]}")
            if '"warnings":["' in txt:
                print("   WARNINGS:", txt[txt.index('"warnings"'):][:300])
            return r

        await call("document_create", width=width, height=190, unit="mm", background="#ffffff")
        box = {"type": "rect", "width": 50, "height": 16, "rx": 3, "fill": "#eef3fb", "stroke": "#2f5d9e",
               "stroke_width": 0.5}
        txt = {"type": "text", "font_size": 5, "font_family": "sans-serif"}
        steps = [("start", "Request"), ("parse", "Parse spec"), ("render", "Render"), ("done", "Return image")]
        els = [dict(box, id=i, rx=8 if i in ("start", "done") else 3) for i, _ in steps]
        els += [dict(txt, id=f"{i}_t", text=t) for i, t in steps]
        els += [{"type": "polygon", "id": "valid", "points": [[25, 0], [50, 12], [25, 24], [0, 12]],
                 "fill": "#fff7e0", "stroke": "#b58900", "stroke_width": 0.5},
                dict(txt, id="valid_t", text="Valid?"),
                dict(box, id="error", fill="#fdecea", stroke="#c0392b"),
                dict(txt, id="error_t", text="Report error")]
        await call("add_elements", elements=els)
        await call("align", operations=[{"ids": [f"{i}_t"], "to": i, "horizontal": "center", "vertical": "middle"}
                                        for i in ["start", "parse", "valid", "render", "done", "error"]])
        main_col = [[i, f"{i}_t"] for i in ["start", "parse", "valid", "render", "done"]]
        await call("layout", items=main_col, direction="column", gap=14, to="page", horizontal="center",
                   vertical="top", margin=12)
        await call("layout", items=[["valid", "valid_t"], ["error", "error_t"]], direction="row", gap=20,
                   align="center")
        await call("connect", connections=[
            {"from": "start", "to": "parse"},
            {"from": "parse", "to": "valid"},
            {"from": "valid", "to": "render", "label": "yes", "stroke": "#2e7d32"},
            {"from": "valid", "to": "error", "label": "no", "stroke": "#c0392b"},
            {"from": "render", "to": "done"},
            {"from": "error", "to": "done", "routing": "elbow", "stroke_dasharray": "1.5 1"},
        ])
        r = await call("render_preview", max_size=700)
        (OUT / f"e10_flowchart_{width}.png").write_bytes(base64.b64decode(r.content[0].data))
        await call("document_save", path=str(OUT / "e10_flowchart.svg"))
    print("tool calls:", calls)


asyncio.run(main(160))
asyncio.run(main(200))
