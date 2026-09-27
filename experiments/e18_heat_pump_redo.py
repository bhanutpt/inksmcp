"""E18: Redo the hard parts of field test 2 (heat-pump poster) with the new features:
loop with from_side/to_side (no helper waypoints), block `arrow` elements, wrapped text (`width`),
chart with grid + plot + axis titles. Count calls, check the zoomed corners and label placement.

Run: uv run python experiments/e18_heat_pump_redo.py
"""
import asyncio
import base64
import time
from pathlib import Path

from mcp import Client, StdioServerParameters

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
RED, BLUE = "#c62828", "#1565c0"


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
            print(f"{name:14s} {(time.perf_counter() - t) * 1000:6.0f} ms err={r.is_error} {txt[:170]}")
            return r

        await call("document_create", width=297, height=210, unit="mm", background="#ffffff")
        box = {"type": "rect", "width": 56, "height": 18, "rx": 2, "stroke_width": 0.8, "layer": "Parts"}
        lab = {"type": "text", "font_size": 4, "font_weight": "bold", "text_anchor": "middle", "layer": "Labels",
               "fill": "#222"}
        await call("add_elements", defaults={"font_family": "Arial"}, elements=[
            {"type": "rect", "x": 12, "y": 30, "width": 160, "height": 60, "rx": 3, "fill": "#fde3e0", "layer": "Zones"},
            {"type": "rect", "x": 12, "y": 90, "width": 160, "height": 60, "rx": 3, "fill": "#e3eefb", "layer": "Zones"},
            dict(box, id="cond", x=62, y=42, fill="#f5b7b1", stroke=RED),
            dict(box, id="evap", x=62, y=122, fill="#b3d1f2", stroke=BLUE),
            {"type": "polygon", "id": "valve", "points": [[30, 78], [44, 90], [30, 102], [16, 90]],
             "fill": "#eee", "stroke": "#444", "stroke_width": 0.8, "layer": "Parts"},
            {"type": "circle", "id": "comp", "cx": 150, "cy": 90, "r": 12, "fill": "#eee", "stroke": "#444",
             "stroke_width": 0.8, "layer": "Parts"},
            dict(lab, id="cond_t", x=0, y=0, text="CONDENSER"), dict(lab, id="evap_t", x=0, y=0, text="EVAPORATOR"),
            dict(lab, id="valve_t", x=0, y=0, text="EXPANSION\nVALVE", font_size=2.4),
            dict(lab, id="comp_t", x=0, y=0, text="COMPRESSOR", font_size=2.6),
            *[{"type": "arrow", "x1": x, "y1": 38, "x2": x, "y2": 24, "shaft_width": 2, "head_width": 5,
               "fill": RED, "layer": "Heat"} for x in (80, 90, 100)],
            *[{"type": "arrow", "x1": x, "y1": 158, "x2": x, "y2": 144, "shaft_width": 2, "head_width": 5,
               "fill": BLUE, "layer": "Heat"} for x in (80, 90, 100)],
            {"type": "text", "id": "steps", "x": 190, "y": 36, "width": 90, "font_size": 3.2, "fill": "#222",
             "line_height": 1.35, "text": "1  Evaporator: cold refrigerant takes heat from the outdoor air and boils "
                                          "into a low-pressure gas.\n2  Compressor: squeezing the gas raises its "
                                          "pressure and its temperature (to roughly 70–90 °C).\n3  Condenser: the "
                                          "hot gas gives its heat to the home and condenses back into a liquid.\n"
                                          "4  Expansion valve: the pressure drops, the liquid turns very cold, and "
                                          "the cycle starts again.", "layer": "Text"},
        ])
        await call("align", operations=[{"ids": [f"{i}_t"], "to": i, "horizontal": "center", "vertical": "middle"}
                                        for i in ("cond", "evap", "valve", "comp")])
        await call("connect", connections=[
            {"from": "comp", "to": "cond", "from_side": "top", "to_side": "right", "routing": "elbow", "stroke": RED,
             "stroke_width": 1.2, "label": "hot gas", "label_offset": 2, "font_family": "Arial", "font_size": 3},
            {"from": "cond", "to": "valve", "from_side": "left", "to_side": "top", "routing": "elbow", "stroke": RED,
             "stroke_width": 1.2, "label": "warm liquid", "label_offset": 2, "font_family": "Arial", "font_size": 3},
            {"from": "valve", "to": "evap", "from_side": "bottom", "to_side": "left", "routing": "elbow",
             "stroke": BLUE, "stroke_width": 1.2, "label": "cold liquid", "label_offset": 2, "font_family": "Arial",
             "font_size": 3},
            {"from": "evap", "to": "comp", "from_side": "right", "to_side": "bottom", "routing": "elbow",
             "stroke": BLUE, "stroke_width": 1.2, "label": "cool gas", "label_offset": 2, "font_family": "Arial",
             "font_size": 3},
        ])
        await call("grid", rect=[200, 110, 84, 70], id_prefix="cop",
                   x={"scale": "linear", "major": 14, "minor": 7, "label_start": -15, "label_step": 5},
                   y={"scale": "linear", "major": 17.5, "minor": 8.75, "label_start": 1, "label_step": 1},
                   labels={"sides": ["left", "bottom"], "font_family": "Arial", "x_title": "Outdoor air temperature (°C)",
                           "y_title": "COP"})
        await call("plot", grid="cop", series=[{"points": [[-15, 2.1], [-10, 2.4], [-5, 2.8], [0, 3.2], [5, 3.7],
                                                           [10, 4.2], [15, 4.7]], "stroke": "#2e7d32",
                                                "point_labels": [None, None, None, "COP 3.2 at 0 °C", None, None, None],
                                                "font_family": "Arial"}])
        r = await call("render_preview", max_size=1400)
        (OUT / "e18_poster.png").write_bytes(base64.b64decode(r.content[0].data))
        r = await call("render_preview", region=[10, 25, 60, 50], max_size=700)
        (OUT / "e18_corner.png").write_bytes(base64.b64decode(r.content[0].data))
    print("tool calls:", calls)


asyncio.run(main())
