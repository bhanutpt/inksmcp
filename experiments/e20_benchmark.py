"""E20: Reference benchmark — tool calls and token cost for a fixed set of tasks.

Each task is the call sequence a well-informed agent would make with today's tools (a lower bound:
no retries, no exploration). Measured per task: calls, request/response characters, preview images
(tokens ≈ w·h/750), wall time. Also the fixed cost of the tool list the client loads once.
Tokens are estimated as chars/4. Re-run after every phase and append the table to docs/08-benchmarks.md.

Run: uv run python experiments/e20_benchmark.py
"""
import asyncio
import base64
import json
import struct
import time
from pathlib import Path

from mcp import Client, StdioServerParameters

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)


class Meter:
    def __init__(self, client):
        self.c = client
        self.reset()

    def reset(self):
        self.calls = self.req = self.resp = self.img_tokens = self.errors = 0
        self.last_image = None

    async def __call__(self, name, **args):
        self.calls += 1
        self.req += len(json.dumps({"name": name, "arguments": args}, ensure_ascii=False))
        r = await self.c.call_tool(name, args)
        self.errors += bool(r.is_error)
        for x in r.content:
            if x.type == "text":
                self.resp += len(x.text)
            elif x.type == "image":
                self.last_image = base64.b64decode(x.data)
                w, h = struct.unpack(">II", self.last_image[16:24])
                self.img_tokens += round(w * h / 750)
        if r.is_error:
            print(f"   ! {name}: {r.content[0].text[:200]}")
        return r

    async def json(self, name, **args):
        r = await self(name, **args)
        return json.loads(next(x.text for x in r.content if x.type == "text"))


# -- tasks ---------------------------------------------------------------------------------------
async def flowchart(call):
    """6-step flowchart with a decision and a loop back, labelled arrows."""
    await call("document_create", width=210, height=297, unit="mm", background="#ffffff")
    steps = ["Order received", "Check stock", "In stock?", "Ship order", "Send invoice", "Reorder"]
    els = []
    for i, s in enumerate(steps):
        shape = ({"type": "polygon", "points": [[30, 0], [60, 15], [30, 30], [0, 15]]} if s.endswith("?")
                 else {"type": "rect", "width": 60, "height": 22, "rx": 3})
        els += [dict(shape, id=f"s{i}", fill="#e3eefb", stroke="#1565c0", stroke_width=0.6),
                {"type": "text", "id": f"s{i}_t", "x": 0, "y": 0, "text": s, "font_size": 4, "text_anchor": "middle"}]
    await call("add_elements", elements=els, defaults={"font_family": "Arial"})
    # labels into their shapes first: layout measures [shape, label] as one unit
    await call("align", operations=[{"ids": [f"s{i}_t"], "to": f"s{i}", "horizontal": "center", "vertical": "middle"}
                                    for i in range(6)])
    await call("layout", items=[[f"s{i}", f"s{i}_t"] for i in (0, 1, 2, 3, 4)], direction="column", gap=12,
               to="page", horizontal="center", vertical="top", margin=20)
    await call("layout", items=[["s2", "s2_t"], ["s5", "s5_t"]], direction="row", gap=30)
    await call("connect", connections=[
        *[{"from": f"s{i}", "to": f"s{i + 1}"} for i in range(4)],
        {"from": "s2", "to": "s5", "from_side": "right", "to_side": "left", "label": "no", "label_offset": 2},
        {"from": "s5", "to": "s1", "from_side": "top", "to_side": "right", "routing": "elbow"}])
    await call("page_fit", margin=10)
    await call("render_preview", max_size=800)


async def graph_paper(call):
    """Field test 1: A4 log-log paper, 3 x 5 cycles, labelled."""
    await call("document_create", width=210, height=297, unit="mm", background="#ffffff")
    await call("grid", rect=[20, 20, 170, 255], x={"scale": "log", "cycles": 3}, y={"scale": "log", "cycles": 5},
               labels={"sides": ["left", "bottom"]})
    await call("render_preview", max_size=800)
    await call("render_preview", max_size=800, region=[15, 240, 50, 40])
    await call("export", path=str(OUT / "e20_graph.pdf"))


async def bar_chart(call):
    """Field test 3's chart: horizontal bars with category names and value labels."""
    bars = [("Wright Flyer", 48), ("Spirit of St. Louis", 214), ("Spitfire I", 582), ("Bell X-1", 1127),
            ("Concorde", 2179)]
    await call("document_create", width=200, height=90, unit="mm", background="#ffffff")
    await call("grid", rect=[50, 10, 140, 60], x={"scale": "linear", "major": 28, "minor": 5.6, "label_step": 500},
               y={"scale": "linear", "major": 12, "lines": False}, border=0,
               labels={"sides": ["bottom"], "bold_major": False, "x_title": "Top speed (km/h)"}, id_prefix="speed")
    r = await call.json("plot", grid="speed", series=[
        {"id": f"bar{i}", "points": [[0, 4.5 - i], [v, 4.5 - i]], "stroke": "#0f2742", "stroke_width": 7,
         "marker": "none", "point_labels": [None, f"{v:,} km/h"], "label_font_size": 3,
         **({"label_offset": [-2, 0], "label_color": "#fff", "label_halo": "none"} if v > 1500
            else {"label_offset": [2, 0]})} for i, (_, v) in enumerate(bars)])
    await call("add_elements", elements=[
        {"type": "text", "x": 48, "y": s["points"][0][1], "text": n, "font_size": 3, "text_anchor": "end",
         "vertical_anchor": "middle"} for (n, _), s in zip(bars, r["series"])])
    await call("render_preview", max_size=800)


async def icon(call):
    """48 px 'cloud upload' icon: union of circles + rect, arrow cut out, PNG export."""
    await call("document_create", width=48, height=48, unit="px")
    await call("add_elements", elements=[
        {"type": "circle", "id": "c1", "cx": 16, "cy": 26, "r": 9, "fill": "#1565c0"},
        {"type": "circle", "id": "c2", "cx": 26, "cy": 20, "r": 11, "fill": "#1565c0"},
        {"type": "circle", "id": "c3", "cx": 35, "cy": 27, "r": 8, "fill": "#1565c0"},
        {"type": "rect", "id": "r1", "x": 16, "y": 26, "width": 19, "height": 9, "fill": "#1565c0"},
        {"type": "arrow", "id": "up", "x1": 25, "y1": 33, "x2": 25, "y2": 18, "shaft_width": 3, "head_width": 9,
         "head_length": 6, "fill": "#000"}])
    await call("path_operation", operation="union", ids=["c1", "c2", "c3", "r1"])  # keeps c1's id (S2)
    await call("path_operation", operation="difference", ids=["c1", "up"])
    await call("render_preview", max_size=256)
    await call("export", path=str(OUT / "e20_icon.png"), width=256)


async def timeline(call):
    """Field test 3's timeline, 4 entries: badge on a spine, card alternating left/right with year,
    title and wrapped text. Positions computed by the agent (no repeat/template tool yet)."""
    rows = [("1903", "First powered flight", "The Wright Flyer stays aloft for 12 seconds at Kitty Hawk."),
            ("1927", "Atlantic solo", "Lindbergh flies New York to Paris non-stop in 33.5 hours."),
            ("1947", "Sound barrier", "Chuck Yeager's Bell X-1 passes Mach 1 over the Mojave Desert."),
            ("1969", "Moon landing", "Apollo 11 lands; Armstrong and Aldrin walk on the Moon.")]
    await call("document_create", width=210, height=160, unit="mm", background="#ffffff")
    els = [{"type": "line", "x1": 105, "y1": 15, "x2": 105, "y2": 150, "stroke": "#b0b8c4", "stroke_width": 1}]
    for i, (year, title, desc) in enumerate(rows):
        y, left = 30 + 34 * i, i % 2 == 0
        x = 15 if left else 118
        els += [{"type": "circle", "id": f"b{i}", "cx": 105, "cy": y, "r": 5, "fill": "#0f2742",
                 "stroke": "#e8742a", "stroke_width": 1},
                {"type": "rect", "id": f"card{i}", "x": x, "y": y - 12, "width": 77, "height": 26, "rx": 2,
                 "fill": "#f3f5f8"},
                {"type": "text", "id": f"y{i}", "x": x + 4, "y": y - 3, "text": year, "font_size": 7,
                 "font_weight": "bold", "fill": "#e8742a"},
                {"type": "text", "id": f"t{i}", "x": x + 26, "y": y - 3, "text": title, "font_size": 4,
                 "font_weight": "bold"},
                {"type": "text", "id": f"d{i}", "x": x + 4, "y": y + 4, "text": desc, "font_size": 3.2,
                 "width": 69}]
    r = await call.json("add_elements", elements=els, defaults={"font_family": "Arial"})
    # card heights follow the wrapped line count
    await call("update_elements", updates=[
        {"id": f"card{i}", "height": 19 + 3.2 * 1.25 * n} for i, n in
        enumerate(r.get("wrapped_lines", {}).get(f"d{i}", 2) for i in range(len(rows)))])
    await call("render_preview", max_size=800)


TASKS = [flowchart, graph_paper, bar_chart, icon, timeline]


async def main():
    params = StdioServerParameters(command="uv", args=["run", "inksmcp"], cwd=str(Path(__file__).parents[1]))
    results = {}
    async with Client(params) as c:
        tools = await c.list_tools()
        tool_chars = len(json.dumps([t.model_dump(exclude_none=True) for t in tools.tools], ensure_ascii=False))
        call = Meter(c)
        await call("inkscape_info")  # warm up (shell start is not part of any task)
        for task in TASKS:
            call.reset()
            t = time.perf_counter()
            await task(call)
            if call.last_image:
                (OUT / f"e20_{task.__name__}.png").write_bytes(call.last_image)
            results[task.__name__] = {
                "calls": call.calls, "errors": call.errors, "req_chars": call.req, "resp_chars": call.resp,
                "img_tokens": call.img_tokens,
                "est_tokens": round((call.req + call.resp) / 4) + call.img_tokens,
                "seconds": round(time.perf_counter() - t, 2)}
    print(f"\ntool list: {len(tools.tools)} tools, {tool_chars} chars ~ {round(tool_chars / 4)} tokens (once per session)\n")
    print("| task | calls | errors | request chars | response chars | image tokens | ~tokens | seconds |")
    print("|---|---|---|---|---|---|---|---|")
    for name, r in results.items():
        print(f"| {name} | {r['calls']} | {r['errors']} | {r['req_chars']:,} | {r['resp_chars']:,} | "
              f"{r['img_tokens']:,} | {r['est_tokens']:,} | {r['seconds']} |")
    (OUT / "e20_benchmark.json").write_text(json.dumps(
        {"tools": len(tools.tools), "tool_chars": tool_chars, "tasks": results}, indent=1), encoding="utf-8")


asyncio.run(main())
