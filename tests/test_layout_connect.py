"""layout + connect: pure maths and real Inkscape behaviour (E09, E09b)."""
import json
import math

import pytest
from mcp import Client

from inksmcp import server
from inksmcp.document import Document, DocumentError, parse_style
from inksmcp.layout import arrange, polyline_midpoint, polyline_points


# -- pure maths ------------------------------------------------------------
def test_arrange_row_column_grid():
    pos, size = arrange([(10, 10), (20, 30)], "row", gap=5, align="center")
    assert pos == [(0, 10), (15, 0)] and size == (35, 30)
    pos, size = arrange([(10, 10), (20, 30)], "column", gap=5, align="start")
    assert pos == [(0, 0), (0, 15)] and size == (20, 45)
    pos, size = arrange([(10, 10), (20, 20), (10, 10)], "grid", gap=(2, 4), columns=2, align="start")
    assert pos == [(0, 0), (12, 0), (0, 24)] and size == (32, 34)
    with pytest.raises(ValueError):
        arrange([(1, 1)], "diagonal")


def test_polyline_parsing_matches_inkscape_output():
    # both forms observed in E09b
    assert polyline_points("M 100,47.5 260,57.5") == [(100, 47.5), (260, 57.5)]
    assert polyline_points("m 100,45 h 80 v 135") == [(100, 45), (180, 45), (180, 180)]
    x, y, _ = polyline_midpoint([(0, 0), (10, 0), (10, 10)])
    assert (x, y) == (10, 0)


# -- engine ------------------------------------------------------------------
@pytest.fixture
def boxes():
    doc = Document.create(300, 200)
    doc.add({"type": "rect", "id": "a", "x": 20, "y": 20, "width": 60, "height": 40, "fill": "#eee"})
    doc.add({"type": "rect", "id": "b", "x": 200, "y": 20, "width": 60, "height": 40, "fill": "#eee"})
    doc.add({"type": "circle", "id": "c", "cx": 230, "cy": 150, "r": 30, "fill": "#eee"})
    doc.add({"type": "text", "id": "t", "x": 30, "y": 150, "text": "note"})
    return doc


def ends(doc, cid):
    pts = polyline_points(doc.get(cid).get("d"))
    return pts[0], pts[-1]


def test_connect_attaches_to_edges(engine, boxes):
    r = engine.connect(boxes, [{"from": "a", "to": "b"}, {"from": "a", "to": "c", "stroke": "#c00"}])
    assert r["warnings"] == []
    (sx, sy), (ex, ey) = ends(boxes, r["ids"][0])
    assert (sx, ex) == pytest.approx((80, 200)) and sy == ey == pytest.approx(40)
    _, (cx, cy) = ends(boxes, r["ids"][1])
    assert math.dist((cx, cy), (230, 150)) == pytest.approx(30, abs=0.1)  # clipped to the circle itself
    markers = boxes.root.xpath("//*[local-name()='marker']/@id")
    assert sorted(markers) == ["inksmcp-arrow-000000", "inksmcp-arrow-c00"]  # one per colour


def test_connectors_follow_layout(engine, boxes):
    [cid] = engine.connect(boxes, [{"from": "a", "to": "b"}])["ids"]
    engine.layout(boxes, ["a", "b"], "column", gap=40, align="start")
    (sx, sy), (ex, ey) = ends(boxes, cid)
    assert sy == pytest.approx(60) and ey == pytest.approx(100)  # a bottom edge -> b top edge
    assert sx == ex


def test_connector_label_sits_on_midpoint(engine, boxes):
    [cid] = engine.connect(boxes, [{"from": "a", "to": "b", "label": "calls"}])["ids"]
    lab = boxes.get(f"{cid}_label")
    assert float(lab.get("x")) == pytest.approx(140)
    b, caps = engine.measure(boxes, [f"{cid}_label"])
    cap_mid = caps[f"{cid}_label"][1] + caps[f"{cid}_label"][3] / 2
    assert cap_mid == pytest.approx(40, abs=0.5)  # cap-centred on the line (approximate metrics)
    engine.align(boxes, [{"ids": ["b"], "to": "page", "vertical": "bottom"}])
    assert float(boxes.get(f"{cid}_label").get("x")) == pytest.approx(140)
    assert float(boxes.get(f"{cid}_label").get("y")) > 60  # followed the connector down


def test_text_endpoint_warns(engine, boxes):
    r = engine.connect(boxes, [{"from": "t", "to": "a"}])
    assert "text" in r["warnings"][0]


def test_connect_errors_roll_back(engine, boxes):
    with pytest.raises(DocumentError, match=r"connections\[1\]"):
        engine.connect(boxes, [{"from": "a", "to": "b"}, {"from": "a", "to": "nope"}])
    assert boxes.connectors() == []


def test_delete_cascades_to_connectors_and_labels(engine, boxes):
    [cid] = engine.connect(boxes, [{"from": "a", "to": "b", "label": "x"}])["ids"]
    assert set(boxes.delete("b")) == {"b", cid, f"{cid}_label"}


def test_layout_items_move_as_units(engine, boxes):
    boxes.add({"type": "text", "id": "a_label", "x": 40, "y": 45, "text": "A"})
    before = engine.bboxes(boxes)
    r = engine.layout(boxes, [["a", "a_label"], "b", "c"], "row", gap=10, align="start", at=(5, 5))
    after = engine.bboxes(boxes)
    assert after["a"][:2] == pytest.approx((5, 5), abs=0.01)
    assert after["b"][0] == pytest.approx(5 + 60 + 10, abs=0.01)
    assert after["c"][0] == pytest.approx(5 + 60 + 10 + 60 + 10, abs=0.01)
    for k in (0, 1):  # label kept its offset inside the box
        assert after["a_label"][k] - after["a"][k] == pytest.approx(before["a_label"][k] - before["a"][k], abs=0.01)
    assert r["block"] == [5, 5, 200, 60]


def test_layout_grid_centred_on_page(engine):
    doc = Document.create(200, 200)
    for i in range(4):
        doc.add({"type": "rect", "id": f"r{i}", "x": 0, "y": 0, "width": 20, "height": 20})
    engine.layout(doc, [f"r{i}" for i in range(4)], "grid", gap=10, columns=2, to="page",
                  horizontal="center", vertical="middle")
    b = engine.bboxes(doc)
    assert [b[f"r{i}"][:2] for i in range(4)] == [pytest.approx(p, abs=0.01) for p in
                                                  [(75, 75), (105, 75), (75, 105), (105, 105)]]


def test_off_page_warning(engine, boxes):
    # E10: the agent didn't notice a box running off the page in the preview.
    r = engine.layout(boxes, ["a", "b", "c"], "row", gap=10)
    assert "warnings" not in r
    r = engine.layout(boxes, ["a", "b", "c"], "row", gap=100)
    assert any("'c'" in w and "right by" in w for w in r["warnings"])


def test_layout_errors(engine, boxes):
    with pytest.raises(DocumentError, match="more than one"):
        engine.layout(boxes, ["a", ["a", "b"]])
    with pytest.raises(DocumentError, match="direction"):
        engine.layout(boxes, ["a", "b"], "diagonal")


# -- MCP tools -----------------------------------------------------------------
@pytest.mark.anyio
async def test_flowchart_via_tools(engine, monkeypatch):
    s = server.Session()
    s._engine = engine
    monkeypatch.setattr(server, "session", s)
    async with Client(server.mcp) as c:
        async def call(name, **args):
            r = await c.call_tool(name, args)
            assert not r.is_error, r.content
            return json.loads(r.content[0].text)

        await call("document_create", width=200, height=300, unit="mm")
        els = []
        for i, name in enumerate(["Start", "Work", "Done"]):
            els += [{"type": "rect", "id": f"s{i}", "x": 0, "y": 0, "width": 50, "height": 20, "rx": 3,
                     "fill": "#eef"}, {"type": "text", "id": f"s{i}_t", "x": 0, "y": 0, "text": name}]
        await call("add_elements", elements=els)
        await call("align", operations=[{"ids": [f"s{i}_t"], "to": f"s{i}", "horizontal": "center",
                                         "vertical": "middle"} for i in range(3)])
        r = await call("connect", connections=[{"from": "s0", "to": "s1"}, {"from": "s1", "to": "s2", "label": "ok"}])
        assert len(r["ids"]) == 2
        r = await call("layout", items=[[f"s{i}", f"s{i}_t"] for i in range(3)], direction="column", gap=25,
                       to="page", horizontal="center", vertical="top", margin=20)
        assert r["block"] == [75, 20, 50, 110]
        outline = (await call("inspect"))["outline"]
        layer = next(n for n in outline if n.get("label") == "Connectors")  # loose ends → a Connectors layer
        conns = [n for n in layer["children"] if n["type"] == "connector"]
        assert {(n["from"], n["to"]) for n in conns} == {("s0", "s1"), ("s1", "s2")}
        c1 = next(n for n in conns if n["from"] == "s0")
        assert c1["bbox"][1] == pytest.approx(40, abs=0.1)  # starts at s0's bottom edge (20 + 20)
        await call("update_elements", updates=[{"id": "s2", "x": 140}])  # connectors re-sync
        r = await call("delete_elements", ids=["s1"])
        assert len(r["deleted"]) == 4  # box + 2 connectors + 1 label
