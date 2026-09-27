"""align: pure maths + real Inkscape behaviour (findings E07/E07b)."""
import json

import pytest
from mcp import Client

from inksmcp import server
from inksmcp.document import Document, DocumentError
from inksmcp.layout import align_delta, union


# -- pure maths ------------------------------------------------------------
def test_align_delta():
    box, ref = (10, 10, 20, 10), (0, 0, 100, 50)
    assert align_delta(box, ref, "left") == (-10, 0)
    assert align_delta(box, ref, "center", "middle") == (30, 10)
    assert align_delta(box, ref, "right", "bottom", margin=5) == (65, 25)
    assert align_delta(box, ref, None, "top", margin=2) == (0, -8)
    assert union([(0, 0, 10, 10), (20, 5, 10, 10)]) == (0, 0, 30, 15)


# -- against Inkscape --------------------------------------------------------
def centre(b):
    return b[0] + b[2] / 2, b[1] + b[3] / 2


@pytest.fixture
def diagram():
    doc = Document.create(240, 120, "mm")
    for id_, label, x in [("client", "Client", 20), ("server", "inksmcp", 95)]:
        doc.add({"type": "rect", "id": id_, "x": x, "y": 45, "width": 50, "height": 30, "fill": "#eee"})
        doc.add({"type": "text", "id": f"{id_}_label", "x": 5, "y": 5, "text": label, "font_size": 6, "layer": "L"})
    return doc


def test_centre_labels_in_boxes_share_baseline(engine, diagram):
    # E06/E07: 'Client' and 'inksmcp' have different visual heights; cap metrics must give equal baselines.
    engine.align(diagram, [
        {"ids": ["client_label"], "to": "client", "horizontal": "center", "vertical": "middle"},
        {"ids": ["server_label"], "to": "server", "horizontal": "center", "vertical": "middle"},
    ])
    boxes, caps = engine.measure(diagram, ["client_label", "server_label"])
    for id_ in ("client", "server"):
        assert centre(boxes[f"{id_}_label"])[0] == pytest.approx(centre(boxes[id_])[0], abs=0.01)
        assert centre(caps[f"{id_}_label"])[1] == pytest.approx(centre(boxes[id_])[1], abs=0.01)
    assert caps["client_label"][1] + caps["client_label"][3] == pytest.approx(
        caps["server_label"][1] + caps["server_label"][3], abs=0.01)  # same baseline


def test_visual_metrics_centre_glyph_bbox(engine, diagram):
    engine.align(diagram, [{"ids": ["server_label"], "to": "server", "vertical": "middle", "text_metrics": "visual"}])
    boxes, _ = engine.measure(diagram)
    assert centre(boxes["server_label"])[1] == pytest.approx(60, abs=0.01)


def test_align_to_page_edges_with_margin_mm(engine, diagram):
    # E07: transform-translate takes px; we convert from user units (mm here).
    r = engine.align(diagram, [{"ids": ["client"], "to": "page", "horizontal": "right", "vertical": "bottom",
                                "margin": 10}])
    assert r["moved"]["client"] == [160, 35]
    boxes, _ = engine.measure(diagram)
    assert boxes["client"] == pytest.approx((180, 80, 50, 30), abs=0.01)


def test_as_group_keeps_relative_positions(engine, diagram):
    engine.align(diagram, [{"ids": ["client", "server"], "to": "page", "horizontal": "center", "as_group": True}])
    boxes, _ = engine.measure(diagram)
    assert boxes["server"][0] - boxes["client"][0] == pytest.approx(75, abs=0.01)
    assert union([boxes["client"], boxes["server"]])[0] == pytest.approx((240 - 125) / 2, abs=0.01)


def test_align_each_to_selection(engine, diagram):
    engine.align(diagram, [{"ids": ["client", "server"], "to": "selection", "vertical": "top"}])
    boxes, _ = engine.measure(diagram)
    assert boxes["client"][1] == boxes["server"][1] == pytest.approx(45, abs=0.01)


def test_align_inside_transformed_group(engine):
    doc = Document.create(100, 100)
    doc.add({"type": "group", "id": "g", "transform": "translate(30,30) scale(2)"})
    doc.add({"type": "rect", "id": "r", "parent": "g", "x": 5, "y": 5, "width": 10, "height": 10})
    engine.align(doc, [{"ids": ["r"], "to": "page", "horizontal": "left", "vertical": "top"}])
    boxes, _ = engine.measure(doc)
    assert boxes["r"] == pytest.approx((0, 0, 20, 20), abs=0.01)


def test_later_operations_see_earlier_moves(engine, diagram):
    r = engine.align(diagram, [
        {"ids": ["client"], "to": "page", "horizontal": "left"},
        {"ids": ["server"], "to": "client", "horizontal": "left"},
    ])
    assert r["bboxes"]["server"][0] == pytest.approx(0, abs=0.01)


def test_align_errors(engine, diagram):
    with pytest.raises(DocumentError, match="nope"):
        engine.align(diagram, [{"ids": ["nope"], "horizontal": "left"}])
    with pytest.raises(DocumentError, match="horizontal and/or vertical"):
        engine.align(diagram, [{"ids": ["client"]}])


# -- MCP tool ------------------------------------------------------------------
@pytest.mark.anyio
async def test_align_tool(engine, monkeypatch):
    s = server.Session()
    s._engine = engine
    monkeypatch.setattr(server, "session", s)
    async with Client(server.mcp) as c:
        await c.call_tool("document_create", {"width": 100, "height": 50})
        await c.call_tool("add_elements", {"elements": [
            {"type": "rect", "id": "box", "x": 10, "y": 10, "width": 40, "height": 20},
            {"type": "text", "id": "t", "x": 0, "y": 0, "text": "Hi"}]})
        r = await c.call_tool("align", {"operations": [
            {"ids": ["t"], "to": "box", "horizontal": "center", "vertical": "middle"}], "preview": True})
        assert not r.is_error, r.content
        data = json.loads(r.content[0].text)
        assert set(data["moved"]) == {"t"}
        assert r.content[1].type == "image"
        r = await c.call_tool("align", {"operations": [{"ids": ["t"], "horizontal": "middle"}]})
        assert r.is_error  # schema validation: 'middle' is vertical
