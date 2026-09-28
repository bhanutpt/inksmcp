"""Round-2 build step 0 (D-024): small fixes from reports 4–10 plus the `clip` and text `halo` keys (E24)."""
import json

import pytest
from mcp import Client

from inksmcp import server, templates
from inksmcp.document import CLIP_ATTR, Document, DocumentError
from inksmcp.layout import polyline_points


@pytest.fixture
def fresh_session(engine, monkeypatch):
    s = server.Session()
    s._engine = engine
    monkeypatch.setattr(server, "session", s)
    return s


def text(r):
    assert not r.is_error, r.content
    return json.loads(r.content[0].text)


# -- clip (reports 5, 8) ----------------------------------------------------------------------------
def test_clip_to_a_panel_follows_the_element(engine):
    doc = Document.create(200, 120, "mm")
    doc.add({"type": "rect", "id": "panel", "x": 20, "y": 20, "width": 60, "height": 40, "fill": "none"})
    doc.add({"type": "group", "id": "cat", "transform": "translate(50,30) scale(2)", "clip": "panel"})
    doc.add({"type": "circle", "id": "body", "parent": "cat", "cx": 10, "cy": 10, "r": 12})
    assert engine.bboxes(doc)["cat"] == pytest.approx((46, 26, 34, 34), abs=0.01)  # cut at the panel (E24 A, B)
    engine.translate(doc, {"cat": (30, 0)})
    assert engine.bboxes(doc)["cat"] == pytest.approx((76, 26, 34, 34), abs=0.01)  # the clip moves along (C)
    assert engine.bboxes(doc)["panel"][2] == pytest.approx(60, abs=0.6)  # the panel itself stays visible
    doc.update("cat", {"clip": [80, 30, 20, 10]})  # replaced, in the parent's coordinates
    clips = doc.root.xpath("//*[@inksmcp:clip]", namespaces={"inksmcp": "urn:inksmcp"})
    assert len(clips) == 1 and clips[0].get(CLIP_ATTR) == "80,30,20,10"
    assert engine.bboxes(doc)["cat"] == pytest.approx((80, 30, 20, 10), abs=0.01)
    doc.update("cat", {"clip": None})
    assert doc.get("cat").get("clip-path") is None
    assert not doc.root.xpath("//*[@inksmcp:clip]", namespaces={"inksmcp": "urn:inksmcp"})
    with pytest.raises(DocumentError, match="itself"):
        doc.update("cat", {"clip": "body"})


@pytest.mark.anyio
async def test_repeat_clips_each_row_to_its_own_frame(fresh_session, engine):
    async with Client(server.mcp) as c:
        await c.call_tool("document_create", {"width": 100, "height": 50, "unit": "mm"})
        r = text(await c.call_tool("repeat", {"template": [
            {"type": "rect", "id": "frame", "x": 5, "y": 5, "width": 20, "height": 20, "fill": "none"},
            {"type": "circle", "id": "big", "cx": 15, "cy": 15, "r": 15, "clip": "frame"}],
            "rows": [{}, {}, {}], "step": [30, 0]}))
        assert r["ids"]["big"] == ["big-1..big-3"]
    boxes = engine.bboxes(fresh_session.docs["doc1"])
    assert boxes["big-3"] == pytest.approx((65, 5, 20, 20), abs=0.01)


# -- halo (report 8) ---------------------------------------------------------------------------
def test_text_halo_key(engine):
    doc = Document.create(100, 60, "mm")
    doc.add({"type": "text", "id": "plain", "x": 10, "y": 20, "text": "Halo", "font_size": 8})
    doc.add({"type": "text", "id": "h", "x": 10, "y": 40, "text": "Halo", "font_size": 8, "halo": "#fff"})
    style = doc.get("h").get("style")
    assert "paint-order:stroke" in style and "stroke:#fff" in style and "stroke-width:2.4" in style
    b = engine.bboxes(doc)
    assert b["h"][2] - b["plain"][2] == pytest.approx(2.4, abs=0.05)  # bbox grows by the width (E24 E)
    doc.update("h", {"halo_width": 1})
    assert "stroke-width:1" in doc.get("h").get("style")
    doc.update("h", {"halo": "none"})
    assert "stroke" not in doc.get("h").get("style")
    with pytest.raises(DocumentError, match="halo colour"):
        doc.update("h", {"halo_width": 1})


# -- repeat (reports 5, 6) -----------------------------------------------------------------------
def test_compact_ids_and_column_order():
    assert templates.compact(["c-1", "c-2", "c-3", "c-5", "x", "c-6", "d-1", "d-2"]) == \
        ["c-1..c-3", "c-5", "x", "c-6", "d-1", "d-2"]
    # 11 legend rows in 2 columns: 6 + 5, filled top to bottom (report 6)
    offs = [templates.offset(i, [50, 10], 2, 11, "column") for i in range(11)]
    assert offs[5] == (0, 50) and offs[6] == (50, 0) and offs[10] == (50, 40)


@pytest.mark.anyio
async def test_repeat_rejects_id_prefix_equal_to_a_template_id(fresh_session):
    async with Client(server.mcp) as c:
        await c.call_tool("document_create", {"width": 100, "height": 50, "unit": "mm"})
        r = await c.call_tool("repeat", {"template": [{"type": "group", "id": "mia"}], "rows": [{}],
                                         "step": [0, 0], "id_prefix": "mia"})
        assert r.is_error and "mia_row" in r.content[0].text


# -- connect (reports 6, 9) -------------------------------------------------------------------------
@pytest.mark.anyio
async def test_connect_layers_labels_and_end_gap(fresh_session, engine):
    async with Client(server.mcp) as c:
        await c.call_tool("document_create", {"width": 200, "height": 100, "unit": "mm"})
        await c.call_tool("add_elements", {"elements": [
            {"type": "rect", "id": "a", "x": 10, "y": 40, "width": 30, "height": 20, "layer": "Nodes"},
            {"type": "rect", "id": "b", "x": 100, "y": 40, "width": 30, "height": 20, "layer": "Nodes"},
            {"type": "text", "id": "t", "x": 160, "y": 52, "text": "Carbon", "layer": "Labels"}]})
        r = text(await c.call_tool("connect", {"connections": [
            {"from": "a", "to": "b", "label": "yes", "id": "ab"},
            {"from": "b", "to": "t", "end_gap": 2, "id": "bt"}]}))
        assert r["layers"] == ["Connectors", "Nodes"]  # shared layer, else a Connectors layer
        assert r["labels"] == {"ab": "ab_label"}
    doc = fresh_session.docs["doc1"]
    end = polyline_points(doc.get("bt").get("d"))[-1]
    assert end[0] == pytest.approx(engine.bboxes(doc)["t"][0] - 2, abs=0.01)  # stops 2 mm short of the text
