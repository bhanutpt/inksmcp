"""E19: Redo the bar chart from field test 3 (flight infographic) with the cheap follow-ups:
x-only gridlines (`"lines": false` on y), series-named ids, `label_halo: "none"` for labels inside
dark bars, `label_anchor: "end"`. Count calls, save a preview, check label centring on the bars.

Run: uv run python experiments/e19_bar_chart_redo.py
"""
import asyncio
import base64
import json
import time
from pathlib import Path

from mcp import Client, StdioServerParameters

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
NAVY, ORANGE = "#0f2742", "#e8742a"
BARS = [("wright", "Wright Flyer", 48), ("spirit", "Spirit of St. Louis", 214), ("spitfire", "Spitfire I", 582),
        ("x1", "Bell X-1", 1127), ("concorde", "Concorde", 2179)]


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
            print(f"{name:14s} {(time.perf_counter() - t) * 1000:6.0f} ms err={r.is_error} {txt[:200]}")
            return r, txt

        await call("document_create", width=200, height=90, unit="mm", background="#ffffff")
        # 0..2500 km/h on x (major 37.5 mm = 500), 5 rows on y (0.5..4.5 centred), y without gridlines
        await call("grid", rect=[50, 10, 150 - 10, 60], color="#9aa5b1",
                   x={"scale": "linear", "major": 28, "minor": 5.6, "label_step": 500},
                   y={"scale": "linear", "major": 12, "label_start": 0, "label_step": 1, "lines": False},
                   labels={"sides": ["bottom"], "bold_major": False, "x_title": "Top speed (km/h)"},
                   border=0, id_prefix="speed")
        series = []
        for row, (sid, _, v) in enumerate(BARS):
            y = 4.5 - row
            inside = v > 1500
            series.append({"id": f"bar_{sid}", "points": [[0, y], [v, y]], "stroke": NAVY, "stroke_width": 7,
                           "marker": "none", "point_labels": [None, f"{v:,} km/h"], "label_font_size": 3,
                           "label_offset": [-2, 0] if inside else [2, 0],
                           "label_color": "#ffffff" if inside else NAVY,
                           **({"label_halo": "none"} if inside else {})})
        _, txt = await call("plot", grid="speed", series=series)
        res = json.loads(txt)
        print("ids:", [s["labels"] for s in res["series"]], res["series"][0]["line"])
        # category names left of the bars, from the returned points
        names = [{"type": "text", "id": f"name_{sid}", "x": 48, "y": s["points"][0][1], "text": name,
                  "font_size": 3, "text_anchor": "end", "vertical_anchor": "middle", "fill": "#222"}
                 for (sid, name, _), s in zip(BARS, res["series"])]
        await call("add_elements", elements=names, defaults={"font_family": "Segoe UI"})
        r, _ = await call("render_preview", max_size=1400)
        img = next(x for x in r.content if x.type == "image")
        (OUT / "e19_bar_chart.png").write_bytes(base64.b64decode(img.data))
    print(f"{calls} calls -> {OUT / 'e19_bar_chart.png'}")


asyncio.run(main())
