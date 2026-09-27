"""rect `fit_to`: a box sized around its content (field report 3)."""
import json

import pytest
from mcp import Client

from inksmcp import server
from inksmcp.document import FIT_ATTR

LONG = "A description long enough to wrap onto several lines inside the card."


@pytest.fixture
async def call(engine, monkeypatch):
    s = server.Session()
    s._engine = engine
    monkeypatch.setattr(server, "session", s)
    async with Client(server.mcp) as c:
        async def call(name, ok=True, **args):
            r = await c.call_tool(name, args)
            assert r.is_error != ok, r.content
            return json.loads(r.content[0].text) if ok else r.content[0].text
        call.session = s
        yield call


def geo(doc, rid):
    el = doc.get(rid)
    return [float(el.get(k)) for k in ("x", "y", "width", "height")]


@pytest.mark.anyio
async def test_fit_around_texts_and_refit_on_edit(call, engine):
    await call("document_create", width=200, height=150, unit="mm")
    r = await call("add_elements", elements=[
        {"type": "rect", "id": "card", "fit_to": ["title", "desc"], "fit_padding": [3, 4], "fill": "#eee"},
        {"type": "text", "id": "title", "x": 20, "y": 30, "text": "Title", "font_size": 6},
        {"type": "text", "id": "desc", "x": 20, "y": 40, "text": LONG, "font_size": 3.5, "width": 60}])
    doc = call.session.docs["doc1"]
    b = engine.bboxes(doc)
    t, d = b["title"], b["desc"]
    x0, y0 = min(t[0], d[0]), t[1]
    x1, y1 = max(t[0] + t[2], d[0] + d[2]), d[1] + d[3]
    assert geo(doc, "card") == pytest.approx([x0 - 4, y0 - 3, x1 - x0 + 8, y1 - y0 + 6], abs=0.01)
    assert r["fitted"]["card"] == pytest.approx(geo(doc, "card"), abs=0.01)
    # editing a target re-fits; the rect stays behind the texts
    h = geo(doc, "card")[3]
    r = await call("update_elements", updates=[{"id": "desc", "text": LONG + " " + LONG}])
    assert r["fitted"]["card"][3] > h + 5 and geo(doc, "card")[3] == pytest.approx(r["fitted"]["card"][3], abs=0.01)
    order = [e.get("id") for e in doc.get("card").getparent()]
    assert order.index("card") < order.index("title")
    # fit_to null frees the rect: later edits leave it alone
    await call("update_elements", updates=[{"id": "card", "fit_to": None}])
    assert doc.get("card").get(FIT_ATTR) is None
    r = await call("update_elements", updates=[{"id": "desc", "text": "short"}])
    assert "fitted" not in r


@pytest.mark.anyio
async def test_fit_height_only_in_transformed_group_and_panel_chain(call, engine):
    await call("document_create", width=200, height=200, unit="mm")
    await call("add_elements", elements=[
        {"type": "group", "id": "g", "transform": "translate(0,50)"},
        {"type": "rect", "id": "card", "parent": "g", "x": 10, "y": 0, "width": 80, "fit_to": ["desc"],
         "fit": "height", "fit_padding": 2},
        {"type": "text", "id": "desc", "parent": "g", "x": 14, "y": 10, "text": LONG, "font_size": 3.5, "width": 70},
        {"type": "rect", "id": "panel", "fit_to": ["card"], "fit_padding": 5, "fill": "none", "stroke": "#000"}])
    doc = call.session.docs["doc1"]
    b = engine.bboxes(doc)
    x, y, w, h = geo(doc, "card")
    assert (x, w) == (10, 80)  # height only: x and width kept
    assert y == pytest.approx(b["desc"][1] - 50 - 2, abs=0.01)  # local coordinates of the group
    assert h == pytest.approx(b["desc"][3] + 4, abs=0.01)
    assert geo(doc, "panel") == pytest.approx([5, y + 50 - 5, 90, h + 10], abs=0.01)
    # the panel follows when the card grows (dependency order)
    await call("update_elements", updates=[{"id": "desc", "text": LONG + " " + LONG}])
    assert geo(doc, "panel")[3] == pytest.approx(geo(doc, "card")[3] + 10, abs=0.01)


@pytest.mark.anyio
async def test_fit_errors(call):
    await call("document_create", width=100, height=100, unit="mm")
    err = await call("add_elements", ok=False, elements=[{"type": "rect", "fit_padding": 2}])
    assert "need fit_to" in err
    err = await call("add_elements", ok=False, elements=[{"type": "rect", "id": "r", "fit_to": ["ghost"]}])
    assert "none of fit_to" in err
    err = await call("add_elements", ok=False, elements=[{"type": "rect", "id": "r2", "fit_to": ["x"], "fit": "all"}])
    assert "fit must be" in err


@pytest.mark.anyio
async def test_repeat_cards_fit_their_own_text(call, engine):
    await call("document_create", width=210, height=150, unit="mm")
    r = await call("repeat", step=[0, 45], mirror={"x": 105}, rows=[{"d": "Short."}, {"d": LONG + " " + LONG}], template=[
        {"type": "group", "id": "card"},
        {"type": "rect", "id": "box", "parent": "card", "x": 15, "y": 10, "width": 77, "fit_to": ["desc"],
         "fit": "height", "fit_padding": 3},
        {"type": "text", "id": "desc", "parent": "card", "x": 19, "y": 20, "text": "{d}", "font_size": 3.5,
         "width": 69}])
    doc = call.session.docs["doc1"]
    assert set(r["fitted"]) == {"box-1", "box-2"} and r["wrapped_lines"]["desc-2"] > 2
    b = engine.bboxes(doc)
    for n in (1, 2):
        box, desc = b[f"box-{n}"], b[f"desc-{n}"]
        assert box[1] + 3 == pytest.approx(desc[1], abs=0.05)  # measured with stroke-less boxes
        assert box[3] == pytest.approx(desc[3] + 6, abs=0.05)
    assert b["box-2"][0] == pytest.approx(210 - 15 - 77, abs=0.05)  # mirrored after fitting
