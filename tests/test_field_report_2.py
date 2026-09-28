"""Fixes and features from docs/development/field-reports/2026-09-27-heat-pump-poster.md (E17)."""
import json
import math

import pytest
from mcp import Client

from inksmcp import grids, layout, server
from inksmcp.document import Document, DocumentError, parse_style
from inksmcp.layout import polyline_points

LABEL = "{http://www.inkscape.org/namespaces/inkscape}label"


# -- bug 1: multi-line text ---------------------------------------------------------------
def line_bottoms(engine, doc, tid):
    spans = [c.get("id") for c in doc.get(tid)]
    b = engine.bboxes(doc)
    return [b[s][1] + b[s][3] for s in spans]


def test_multiline_text_has_even_line_spacing(engine):
    # E17: role=line tspans with dy doubled the first gap (22.4 -> 47.4 -> 59.9).
    doc = Document.create(100, 100)
    doc.add({"type": "text", "id": "t", "x": 10, "y": 20, "text": "Hxy\nHxy\nHxy", "font_size": 10})
    a, b, c = line_bottoms(engine, doc, "t")
    assert b - a == pytest.approx(12.5, abs=0.05) and c - b == pytest.approx(12.5, abs=0.05)
    doc.update("t", {"line_height": 1.6})
    a, b, c = line_bottoms(engine, doc, "t")
    assert b - a == pytest.approx(16, abs=0.05) and c - b == pytest.approx(16, abs=0.05)
    doc.update("t", {"y": 50, "font_size": 5})  # explicit tspan y follow position and size
    a, b, _ = line_bottoms(engine, doc, "t")
    assert b - a == pytest.approx(8, abs=0.05) and 50 < a < 52


def test_indents_are_preserved():
    doc = Document.create(100, 100)
    doc.add({"type": "text", "id": "t", "x": 0, "y": 10, "text": "1  Step\n   continued"})
    assert doc.get("t").get("{http://www.w3.org/XML/1998/namespace}space") == "preserve"


# -- bug 2 + arrows ----------------------------------------------------------------------------
def test_arrowheads_have_a_flat_front_and_plain_lines_can_use_them():
    doc = Document.create(100, 100)
    lid = doc.add({"type": "line", "x1": 0, "y1": 0, "x2": 50, "y2": 0, "stroke": "#c00", "marker_end": "arrow"})
    style = parse_style(doc.get(lid).get("style"))
    assert style["marker-end"] == "url(#inksmcp-arrow-c00)"
    assert doc.get("inksmcp-arrow-c00")[0].get("d") == "M 0,0 L 10,4 L 10,6 L 0,10 z"  # E17: no stub past the tip
    doc.update(lid, {"marker_end": "none"})
    assert "marker-end" not in parse_style(doc.get(lid).get("style"))


def test_block_arrow_element(engine):
    doc = Document.create(100, 100)
    aid = doc.add({"type": "arrow", "x1": 50, "y1": 90, "x2": 50, "y2": 60, "shaft_width": 2, "head_width": 5,
                   "head_length": 4, "fill": "#c62828"})
    b = engine.bboxes(doc)[aid]
    assert b == pytest.approx((47.5, 60, 5, 30), abs=0.01)
    doc.update(aid, {"y2": 40})  # regenerated from stored parameters
    assert engine.bboxes(doc)[aid] == pytest.approx((47.5, 40, 5, 50), abs=0.01)
    with pytest.raises(DocumentError, match="differ"):
        doc.add({"type": "arrow", "x1": 1, "y1": 1, "x2": 1, "y2": 1})
    assert [e for e in doc.root.iter() if e.get("id", "").startswith("arrow")] == [doc.get(aid)]  # no leftovers


# -- text wrapping ---------------------------------------------------------------------------
def test_wrap_to_width(engine):
    doc = Document.create(200, 100, "mm")
    doc.add({"type": "text", "id": "p", "x": 10, "y": 10, "font_size": 3, "width": 60,
             "text": "Compressor: squeezing the gas raises its pressure and its temperature to roughly 70 to 90 degrees.\nNew paragraph."})
    lines = engine.wrap_texts(doc, ["p"])["p"]
    assert lines >= 3
    b = engine.bboxes(doc)
    widths = [b[c.get("id")][2] for c in doc.get("p")]
    assert max(widths) <= 60 + 0.5 and max(widths) > 40
    assert "".join(doc.get("p")[-1].itertext()) == "New paragraph."  # explicit break kept
    doc.update("p", {"width": 120})
    assert engine.wrap_texts(doc, ["p"])["p"] < lines  # re-wraps from the original text


@pytest.mark.parametrize("family", ["sans-serif", "serif", "monospace", "Consolas", "Palatino Linotype", "Ink Free"])
def test_wrapped_lines_fit_in_any_font(engine, family):
    # summed word widths overflowed by up to 2.3 % (Consolas; DejaVu and Helvetica on CI, 2026-09-28)
    doc = Document.create(200, 100, "mm")
    doc.add({"type": "text", "id": "p", "x": 10, "y": 10, "font_size": 3.5, "width": 50, "font_family": family,
             "text": "Wavy, jagged glyphs: AVAWAY, Tyffany's kerfuffle wiggled; quality joyfully zigzags over lazy "
                     "yellow jackals. W. Y. T. V. A. L'Ours. The quick brown fox jumps over the lazy dog, fjord "
                     "waltz, vexing quiz."})
    engine.wrap_texts(doc, ["p"])
    b = engine.bboxes(doc)
    widths = [b[c.get("id")][2] for c in doc.get("p")]
    assert max(widths) <= 50 * 1.002 and max(widths) > 35, widths


# -- connectors: sides, via, labels ------------------------------------------------------------
def test_route_elbow_textbook_cases():
    cond, valve, evap = (60, 20, 40, 20), (10, 60, 20, 20), (60, 100, 40, 20)
    pts = layout.route_elbow(cond, valve, "left", "top", stub=3)
    assert pts == [(60, 30), (20, 30), (20, 60)]  # left, then down into the valve's top
    pts = layout.route_elbow(valve, evap, "bottom", "left", stub=3)
    assert pts == [(20, 80), (20, 110), (60, 110)]
    pts = layout.route_elbow(cond, evap, "right", "right", stub=3)  # U-turn around the right
    assert pts[0] == (100, 30) and pts[-1] == (100, 110) and max(p[0] for p in pts) == 103


@pytest.fixture
def loop():
    doc = Document.create(200, 150, "mm")
    doc.add({"type": "rect", "id": "cond", "x": 60, "y": 20, "width": 40, "height": 20})
    doc.add({"type": "polygon", "id": "valve", "points": [[20, 60], [30, 70], [20, 80], [10, 70]]})
    doc.add({"type": "rect", "id": "evap", "x": 60, "y": 100, "width": 40, "height": 20})
    return doc


def test_connect_with_sides_and_label_beside_the_line(engine, loop):
    r = engine.connect(loop, [
        {"from": "cond", "to": "valve", "from_side": "left", "to_side": "top", "routing": "elbow",
         "label": "warm liquid", "label_offset": 2},
        {"from": "valve", "to": "evap", "from_side": "bottom", "to_side": "left", "routing": "elbow"},
    ])
    c1, c2 = r["ids"]
    assert polyline_points(loop.get(c1).get("d")) == [(60, 30), (20, 30), (20, 60)]
    assert polyline_points(loop.get(c2).get("d")) == [(20, 80), (20, 110), (60, 110)]
    lab = loop.get(f"{c1}_label")
    assert float(lab.get("x")) == pytest.approx(40) and float(lab.get("y")) == pytest.approx(28)  # above the line
    engine.layout(loop, ["cond"], at=(70, 10))  # moves: our routes follow
    assert polyline_points(loop.get(c1).get("d"))[0] == pytest.approx((70, 20), abs=0.01)
    assert json.loads(loop.get(c1).get("{urn:inksmcp}route"))["from_side"] == "left"


def test_via_waypoints_and_delete_cascade(engine, loop):
    [cid] = engine.connect(loop, [{"from": "cond", "to": "evap", "from_side": "left", "to_side": "left",
                                   "via": [[40, 30], [40, 110]]}])["ids"]
    assert polyline_points(loop.get(cid).get("d")) == [(60, 30), (40, 30), (40, 110), (60, 110)]
    assert cid in loop.delete("evap")


def test_routed_connector_in_transformed_layer(engine, loop):
    loop.layer("Flow").set("transform", "translate(-10,-5)")
    [cid] = engine.connect(loop, [{"from": "cond", "to": "evap", "from_side": "bottom", "to_side": "top",
                                   "layer": "Flow"}])["ids"]
    b = engine.bboxes(loop)[cid]
    assert b[0] + b[2] / 2 == pytest.approx(80, abs=0.5) and b[1] == pytest.approx(40, abs=0.5)


# -- plot on grid ------------------------------------------------------------------------------
def test_axis_mapper():
    f = grids.axis_mapper({"scale": "linear", "major": 14, "label_start": -15, "label_step": 5}, 84)
    assert f(-15) == 0 and f(0) == pytest.approx(42)
    g = grids.axis_mapper({"scale": "log", "cycles": 2, "start": 10}, 100)
    assert g(10) == 0 and g(100) == pytest.approx(50) and g(1000) == pytest.approx(100)


def test_plot_cop_chart(engine):
    doc = Document.create(297, 210, "mm")
    engine.grid(doc, [197, 96, 84, 90], {"scale": "linear", "major": 14, "minor": 7, "label_start": -15, "label_step": 5},
                {"scale": "linear", "major": 22.5, "minor": 11.25, "label_start": 1, "label_step": 1},
                labels={"sides": ["left", "bottom"], "x_title": "Outdoor air temperature (°C)", "y_title": "COP"})
    r = engine.plot(doc, "grid", [{"points": [[-15, 2.1], [0, 3.2], [15, 4.7]], "stroke": "#2e7d32",
                                   "point_labels": [None, "COP 3.2 at 0 °C", None]},
                                  {"points": [[20, 3]], "line": False}])
    s = r["series"][0]
    assert s["points"][1] == pytest.approx([197 + 42, 96 + 90 - 2.2 * 22.5])
    assert len(s["markers"]) == 3 and len(s["labels"]) == 1
    assert "outside the grid" in r["warnings"][0]
    layers = [l.get(LABEL) for l in doc.layers()]
    assert layers[-1] == "Grid data"
    b = engine.bboxes(doc)
    ytitle, xtitle = b["grid-y-title"], b["grid-x-title"]
    left_labels = min(b[i][0] for i in b if i.startswith("grid-label") and b[i][0] < 197)
    assert ytitle[0] + ytitle[2] < left_labels and ytitle[3] > ytitle[2]  # left of the labels, rotated
    assert xtitle[1] > 96 + 90 + 2 and abs(xtitle[0] + xtitle[2] / 2 - (197 + 42)) < 0.5
    with pytest.raises(DocumentError, match="No grid"):
        engine.plot(doc, "nope", [{"points": [[0, 0]]}])


# -- move_to_layer position ----------------------------------------------------------------
def test_move_to_layer_bottom(engine):
    doc = Document.create(100, 100)
    for i in range(3):
        doc.add({"type": "circle", "id": f"c{i}", "cx": 5, "cy": 5, "r": 2, "layer": "Data"})
    doc.add({"type": "polyline", "id": "line", "points": [[0, 0], [9, 9]]})
    engine.move_to(doc, ["line"], "Data", position="bottom")
    assert [c.get("id") for c in doc.layer("Data")] == ["line", "c0", "c1", "c2"]


# -- MCP --------------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_tools_from_field_report_2(engine, monkeypatch):
    s = server.Session()
    s._engine = engine
    monkeypatch.setattr(server, "session", s)
    async with Client(server.mcp) as c:
        async def call(name, **args):
            r = await c.call_tool(name, args)
            assert not r.is_error, r.content
            return json.loads(r.content[0].text)

        await call("document_create", width=200, height=150, unit="mm")
        await call("add_elements", elements=[
            {"type": "rect", "id": "a", "x": 10, "y": 10, "width": 30, "height": 20},
            {"type": "rect", "id": "b", "x": 100, "y": 80, "width": 30, "height": 20},
            {"type": "text", "id": "p", "x": 10, "y": 50, "width": 40, "font_size": 3,
             "text": "A long paragraph that must wrap onto several lines here."}])
        assert len(s.docs["doc1"].get("p")) > 1  # wrapped via add_elements
        r = await call("connect", connections=[{"from": "a", "to": "b", "from_side": "right", "to_side": "top",
                                                "routing": "elbow", "label": "flow", "label_offset": 2,
                                                "font_family": "Arial", "label_halo": "none"}])
        lab = s.docs["doc1"].get(f"{r['ids'][0]}_label")
        st = parse_style(lab.get("style"))
        assert st["font-family"] == "Arial" and "paint-order" not in st
        await call("grid", rect=[20, 60, 60, 60], x={"scale": "linear", "major": 10},
                   y={"scale": "log", "cycles": 2, "start": 1}, id_prefix="chart")
        r = await call("plot", grid="chart", series=[{"points": [[0, 1], [3, 10], [6, 100]]}])
        assert r["series"][0]["points"][-1] == pytest.approx([80, 60])
