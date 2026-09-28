"""page_fit / page_resize (E11)."""
import json

import pytest
from mcp import Client

from inksmcp import server
from inksmcp.document import Document, DocumentError
from inksmcp.layout import parse_transform, polyline_points


# -- pure lxml ---------------------------------------------------------------
def test_set_page_size_keeps_unit_and_resizes_background():
    doc = Document.create(200, 150, "mm", background="#fff")
    assert doc.page_backgrounds() == ["background"]
    assert doc.set_page_size(100, 90) == ["background"]
    assert (doc.root.get("width"), doc.root.get("height"), doc.root.get("viewBox")) == ("100mm", "90mm", "0 0 100 90")
    bg = doc.get("background")
    assert [bg.get(k) for k in ("x", "y", "width", "height")] == ["0", "0", "100", "90"]


def test_set_page_size_keeps_scale_ratio():
    doc = Document.from_bytes(b'<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="50mm" viewBox="0 0 400 200"/>')
    doc.set_page_size(200, 100)
    assert (doc.root.get("width"), doc.root.get("height")) == ("50mm", "25mm")
    doc = Document.from_bytes(b'<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200"/>')
    doc.set_page_size(30, 20)
    assert (doc.root.get("width"), doc.root.get("viewBox")) == ("30", "0 0 30 20")


def test_only_exact_page_covering_rects_are_backgrounds():
    doc = Document.create(100, 100)
    doc.add({"type": "rect", "id": "almost", "x": 0, "y": 0, "width": 100, "height": 99})
    doc.add({"type": "rect", "id": "bg", "x": 0, "y": 0, "width": 100, "height": 100})
    doc.add({"type": "rect", "id": "layered", "x": 0, "y": 0, "width": 100, "height": 100, "layer": "L"})
    assert doc.page_backgrounds() == ["bg"]


# -- against Inkscape -----------------------------------------------------------
@pytest.fixture
def e11():
    doc = Document.create(200, 150, "mm", background="#ffffff")
    doc.add({"type": "rect", "id": "a", "x": 40, "y": 30, "width": 30, "height": 20, "layer": "L"})
    doc.add({"type": "rect", "id": "b", "x": 100, "y": 70, "width": 20, "height": 30, "layer": "L"})
    doc.add({"type": "circle", "id": "c", "cx": 60, "cy": 90, "r": 5})  # top-level, not in a layer
    return doc


def test_page_fit_with_margin(engine, e11):
    r = engine.page_fit(e11, margin=10)
    assert r["page"] == {"width": 100, "height": 90, "unit": "mm"}
    assert r["content_moved_by"] == [-30, -20]
    b = engine.bboxes(e11)
    assert b["a"] == pytest.approx((10, 10, 30, 20), abs=0.01)
    assert b["c"] == pytest.approx((25, 65, 10, 10), abs=0.01)
    assert b["background"] == pytest.approx((0, 0, 100, 90), abs=0.01)


def test_page_fit_per_side_margins_and_ids(engine, e11):
    r = engine.page_fit(e11, margin=[1, 2, 3, 4], ids=["a"])
    assert r["page"]["width"] == 30 + 2 + 4 and r["page"]["height"] == 20 + 1 + 3
    b = engine.bboxes(e11)
    assert b["a"][:2] == pytest.approx((4, 1), abs=0.01)
    assert b["b"][:2] == pytest.approx((64, 41), abs=0.01)  # moved along, composition kept


def test_page_fit_moves_connectors_along(engine, e11):
    [cid] = engine.connect(e11, [{"from": "a", "to": "b"}])["ids"]  # loose ends: a "Connectors" layer
    engine.page_fit(e11, margin=5)
    b = engine.bboxes(e11)
    tx, ty = parse_transform(e11.get(cid).getparent().get("transform"))[4:]  # the layer moved along
    pts = [(x + tx, y + ty) for x, y in polyline_points(e11.get(cid).get("d"))]
    start, end = pts[0], pts[-1]
    ax, ay, aw, ah = b["a"]
    bx, by, bw, bh = b["b"]
    assert ax <= start[0] <= ax + aw + 0.01 and ay <= start[1] <= ay + ah + 0.01
    assert bx - 0.01 <= end[0] <= bx + bw and by - 0.01 <= end[1] <= by + bh


def test_page_fit_moves_layered_connectors_along(engine, e11):
    [cid] = engine.connect(e11, [{"from": "a", "to": "b", "layer": "L", "label": "x"}])["ids"]
    before = e11.get(cid).get("d")
    r = engine.page_fit(e11, margin=5)
    assert r["content_moved_by"] == [-35, -25]
    # the layer carries the (snapped) translation; the route inside it is unchanged
    assert e11.get(cid).getparent().get("transform") == "translate(-35,-25)"
    assert e11.get(cid).get("d") == before
    b = engine.bboxes(e11)
    assert b[f"{cid}_label"][0] > b["a"][0]  # label moved with the drawing


def test_translating_a_connector_directly_is_ignored(engine, e11):
    [cid] = engine.connect(e11, [{"from": "a", "to": "b"}])["ids"]
    before = e11.get(cid).get("d")
    engine.translate(e11, {cid: (50, 50)})
    assert e11.get(cid).get("d") == before


def test_page_fit_normalises_nonzero_viewbox_origin(engine):
    # E11: query-all is relative to the viewBox origin; our bboxes() adds it back.
    doc = Document.from_bytes(b'<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="90mm" '
                              b'viewBox="30 20 100 90"><rect id="r" x="40" y="30" width="10" height="10"/></svg>')
    assert engine.bboxes(doc)["r"] == pytest.approx((40, 30, 10, 10), abs=0.01)
    engine.page_fit(doc, margin=2)
    assert doc.root.get("viewBox") == "0 0 14 14"
    assert engine.bboxes(doc)["r"] == pytest.approx((2, 2, 10, 10), abs=0.01)


def test_page_fit_errors(engine):
    with pytest.raises(DocumentError, match="Nothing visible"):
        engine.page_fit(Document.create(10, 10, background="#fff"))
    with pytest.raises(DocumentError, match="margin"):
        engine.page_fit(Document.create(10, 10), margin=[1, 2, 3])


# -- MCP tools -----------------------------------------------------------------
@pytest.mark.anyio
async def test_page_tools(engine, monkeypatch):
    s = server.Session()
    s._engine = engine
    monkeypatch.setattr(server, "session", s)
    async with Client(server.mcp) as c:
        async def call(name, **args):
            r = await c.call_tool(name, args)
            assert not r.is_error, r.content
            return json.loads(r.content[0].text)

        await call("document_create", width=100, height=100, unit="mm", background="#fafafa")
        await call("add_elements", elements=[{"type": "rect", "id": "r", "x": 45, "y": 45, "width": 10, "height": 10}])
        r = await call("page_resize", width=210, height=297, anchor="center")
        assert r["page"]["width"] == 210 and "warnings" not in r
        b = engine.bboxes(s.docs["doc1"])
        assert b["r"] == pytest.approx((100, 143.5, 10, 10), abs=0.01)
        r = await call("page_resize", width=50, height=50)
        assert "'r'" in r["warnings"][0]
        r = await call("page_fit", margin=5)
        assert r["page"]["width"] == 20 and r["backgrounds_resized"] == ["background"]
