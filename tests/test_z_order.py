"""z_order / move_to_layer (E13) and affine helpers."""
import json

import pytest
from mcp import Client

from inksmcp import server
from inksmcp.document import Document, DocumentError
from inksmcp.layout import format_transform, mat_inv, mat_mul, parse_transform

LABEL = "{http://www.inkscape.org/namespaces/inkscape}label"


# -- affine maths --------------------------------------------------------------
def test_transforms():
    assert format_transform(parse_transform("translate(10,5) translate(-10,-5)")) == ""
    assert format_transform(parse_transform("translate(-34.9999999,2)")) == "translate(-35,2)"
    m = parse_transform("rotate(90 10 10)")
    assert (m[0] * 20 + m[2] * 10 + m[4], m[1] * 20 + m[3] * 10 + m[5]) == pytest.approx((10, 20))
    s = parse_transform("translate(30,30) scale(2)")
    assert mat_mul(s, mat_inv(s)) == pytest.approx((1, 0, 0, 1, 0, 0))
    assert format_transform(s) == "matrix(2,0,0,2,30,30)"
    assert format_transform((1, 0, 0, 1, 123456.7, 0)) == "translate(123456.7,0)"


# -- lxml ------------------------------------------------------------------------
def order(doc, layer="L"):
    lay = next(l for l in doc.layers() if l.get(LABEL) == layer)
    return [c.get("id") for c in lay]


@pytest.fixture
def e13():
    doc = Document.create(200, 100)
    for id_, x, y, s in [("a", 10, 10, 30), ("b", 150, 60, 10), ("c", 20, 20, 30), ("d", 170, 60, 10)]:
        doc.add({"type": "rect", "id": id_, "x": x, "y": y, "width": s, "height": s, "layer": "L"})
    doc.add({"type": "rect", "id": "z", "x": 60, "y": 10, "width": 20, "height": 20, "layer": "Other"})
    doc.layer("Other").set("transform", "translate(-35,-25)")
    return doc


def test_front_back_keep_relative_order(e13):
    e13.z_order(["b", "a"], "front")
    assert order(e13) == ["c", "d", "a", "b"]
    e13.z_order(["d", "b"], "back")
    assert order(e13) == ["d", "b", "c", "a"]


def test_above_below_same_parent(e13):
    e13.z_order(["d"], "below", "a")
    assert order(e13) == ["d", "a", "b", "c"]
    e13.z_order(["d", "a"], "above", "c")
    assert order(e13) == ["b", "c", "d", "a"]


def test_containment_and_bad_targets(e13):
    with pytest.raises(DocumentError, match="contains"):
        e13.z_order(["a"], "above", "a")
    with pytest.raises(DocumentError, match="contains"):
        e13.z_order([e13.layer("L").get("id")], "above", "a")
    with pytest.raises(DocumentError, match="not a layer"):
        e13.move_to(["a"], "b")


# -- against Inkscape -------------------------------------------------------------
def test_cross_layer_moves_keep_visual_position(engine, e13):
    before = engine.bboxes(e13)
    engine.z_order(e13, ["z"], "above", "c")  # from translated layer 'Other' into 'L'
    assert order(e13) == ["a", "b", "c", "z", "d"]
    assert e13.get("z").get("transform") == "translate(-35,-25)"
    assert engine.bboxes(e13)["z"] == pytest.approx(before["z"], abs=0.01)
    engine.move_to(e13, ["a", "z"], "Other")  # and back into the translated layer
    assert [c.get("id") for c in e13.layer("Other")] == ["a", "z"]
    assert e13.get("z").get("transform") is None and e13.get("a").get("transform") == "translate(35,25)"
    after = engine.bboxes(e13)
    for k in ("a", "z"):
        assert after[k] == pytest.approx(before[k], abs=0.01)


def test_move_to_new_layer_and_group(engine, e13):
    r = engine.move_to(e13, ["b"], "Top")
    assert e13.layers()[-1].get(LABEL) == "Top" and r["positions"]["b"]["index"] == 0
    e13.add({"type": "group", "id": "g", "layer": "L", "transform": "scale(2)"})
    before = engine.bboxes(e13)["d"]
    engine.move_to(e13, ["d"], "g")
    assert engine.bboxes(e13)["d"] == pytest.approx(before, abs=0.01)


def test_forward_backward_are_overlap_based(engine, e13):
    # E13: raise skips non-overlapping siblings; lower with nothing overlapping below does nothing.
    r = engine.z_order(e13, ["a"], "forward")
    assert order(e13) == ["b", "c", "a", "d"] and "notes" not in r
    r = engine.z_order(e13, ["d"], "backward")
    assert order(e13) == ["b", "c", "a", "d"] and "'d' unchanged" in r["notes"][0]


def test_connectors_survive_reparenting(engine, e13):
    [cid] = engine.connect(e13, [{"from": "a", "to": "z"}])["ids"]
    engine.move_to(e13, ["z", cid], "L")
    b = engine.bboxes(e13)
    assert e13.get(cid).get("transform") is None
    x0, y0, w, h = b[cid]
    assert b["a"][0] <= x0 + w and x0 <= b["z"][0] + b["z"][2]  # still spans a..z


# -- MCP tools ---------------------------------------------------------------------
@pytest.mark.anyio
async def test_z_order_tools(engine, monkeypatch):
    s = server.Session()
    s._engine = engine
    monkeypatch.setattr(server, "session", s)
    async with Client(server.mcp) as c:
        await c.call_tool("document_create", {"width": 100, "height": 100})
        await c.call_tool("add_elements", {"elements": [
            {"type": "rect", "id": "back", "x": 0, "y": 0, "width": 50, "height": 50, "fill": "red"},
            {"type": "circle", "id": "front", "cx": 25, "cy": 25, "r": 20, "fill": "blue"}]})
        r = await c.call_tool("z_order", {"ids": ["back"], "operation": "front"})
        assert json.loads(r.content[0].text)["positions"]["back"]["index"] == 1
        r = await c.call_tool("z_order", {"ids": ["back"], "operation": "above"})
        assert r.is_error and "target" in r.content[0].text
        r = await c.call_tool("move_to_layer", {"ids": ["front"], "layer": "Highlights"})
        assert not r.is_error, r.content
