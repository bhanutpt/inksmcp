"""Round-2 build step 2 (D-024, D-027): automatic overlap warnings, stored `place`, layout anchors (E27)."""
import json
import re

import pytest
from mcp import Client

from inksmcp import checks, server
from inksmcp.document import Document, DocumentError


@pytest.fixture
def fresh_session(engine, monkeypatch):
    s = server.Session()
    s._engine = engine
    monkeypatch.setattr(server, "session", s)
    return s


def text(r):
    assert not r.is_error, r.content
    return json.loads(r.content[0].text)


# -- pure checks ------------------------------------------------------------------------------------
def test_check_geometry():
    assert checks.path_segments("M 0,0 H 10 M 20,0 l 0,10 Z") == [((0, 0), (10, 0)), ((20, 0), (20, 10)), ((20, 10), (20, 0))]
    with pytest.raises(ValueError):
        checks.path_segments("M 0,0 C 1,1 2,2 3,3")
    box = (10, 10, 10, 4)
    assert checks.segment_hits((0, 12), (30, 12), box, 0.1) and not checks.segment_hits((0, 20), (30, 20), box, 0.1)
    assert checks.stacked({"a": (0, 0, 5, 5), "b": (0, 0, 9, 2), "c": (0, 0, 1, 1), "d": (40, 0, 1, 1)}, {}, 0.1) == {"a", "b", "c"}
    texts = {"lab": (12, 11, 6, 2)}
    bar = {"bar": ((10, 10, 30, 4), [((10, 12), (40, 12))], 4.0)}  # a 4-wide bar with its value label on it
    assert checks.find(texts, {}, bar, {"lab"}, set(), set(), 0.1) == []
    thin = {"rule": ((10, 12, 30, 0.2), [((10, 12), (40, 12))], 0.2)}
    assert checks.find(texts, {}, thin, {"lab"}, set(), set(), 0.1) == [
        "text 'lab' is crossed by 'rule' (give it a halo if that is intended)."]


def test_covers_and_grouping():
    ident = (1, 0, 0, 1, 0, 0)
    box = (1, 1, 8, 3)
    assert checks.covers(("rect", (0, 0, 10, 5, 0, 0), ident), box)
    assert not checks.covers(("rect", (0, 0, 10, 5, 2, 2), ident), (0.3, 0.3, 9, 4))  # a corner lies in the rounding
    assert checks.covers(("rect", (0, 0, 10, 5, 2, 2), ident), box)
    assert checks.covers(("rect", (0, 0, 10, 5, 0.5, 0.5), ident), box)
    assert checks.covers(("ellipse", (5, 2.5, 7, 4), ident), box) and not checks.covers(("ellipse", (5, 2.5, 4.5, 2.5), ident), box)
    notch = [(0, 0), (10, 0), (10, 5), (6, 5), (5, 2), (4, 5), (0, 5)]  # corners inside, an edge through the box
    assert checks.covers(("polygon", notch[:3] + [(0, 5)], ident), box) and not checks.covers(("polygon", notch, ident), box)
    assert checks.covers(("rect", (0, 0, 10, 5, 0, 0), (0.5, 0, 0, 0.5, 0, 0)), (1, 1, 16, 8))  # inverse of scale(2)
    # text on its own opaque box above a pattern: the pattern's edges don't count, the box's still do
    texts = {"t": (12, 11, 6, 2)}
    areas = {"stripe-1": (0, 0, 13, 30), "stripe-2": (15, 0, 2, 30), "stripe-3": (16, 0, 3, 30)}
    order = {"stripe-1": 1, "stripe-2": 2, "stripe-3": 3, "box": 4, "t": 5}
    assert checks.find(texts, areas, {}, {"t"}, set(), set(), 0.1) == [
        "text 't' crosses the edges of 3 shapes: 'stripe-1', 'stripe-2', 'stripe-3'."]
    assert checks.find(texts, areas, {}, {"t"}, set(), set(), 0.1, order=order, cover={"t": 4}) == []
    assert checks.find(texts, areas, {}, {"t"}, set(), set(), 0.1, order={**order, "stripe-3": 6}, cover={"t": 4}) == [
        "text 't' crosses the edge of 'stripe-3'."]


@pytest.mark.anyio
async def test_no_warnings_for_what_an_opaque_box_hides(fresh_session):
    # comic page 2 (2026-09-28): 15 warnings from wallpaper stripes under balloons and captions
    async with Client(server.mcp) as c:
        await c.call_tool("document_create", {"width": 170, "height": 60, "unit": "mm"})
        text(await c.call_tool("repeat", {"id_prefix": "stripes", "step": [6, 0], "layer": "Wall",
                                          "rows": [{}] * 28, "template": [
            {"type": "rect", "id": "stripe", "x": 0, "y": 0, "width": 3, "height": 60, "fill": "#f6e1b5"}]}))
        r = text(await c.call_tool("add_elements", {"elements": [
            {"type": "rect", "id": "balloon", "x": 10, "y": 10, "width": 70, "height": 12, "rx": 3, "fill": "#fff",
             "stroke": "#222", "stroke_width": 0.5, "layer": "Balloons"},  # roomy: text widths differ by font
            {"type": "text", "id": "said", "x": 45, "y": 17.5, "text": "Challenge accepted.", "font_size": 4,
             "text_anchor": "middle", "layer": "Balloons"},
            {"type": "rect", "id": "glass", "x": 90, "y": 10, "width": 70, "height": 12, "fill": "#fff",
             "opacity": 0.5, "layer": "Balloons"},
            {"type": "text", "id": "seen", "x": 125, "y": 17.5, "text": "Through glass", "font_size": 4,
             "text_anchor": "middle", "layer": "Balloons"}]}))
        w = r["warnings"]
        assert len(w) == 1 and w[0].startswith("text 'seen' crosses the edges of "), w  # half-transparent: still seen
        # a text pushed half out of its balloon: the balloon's own edge and the stripes beside it are real again
        r = text(await c.call_tool("update_elements", {"updates": [{"id": "said", "x": 12}]}))
        assert any(x.startswith("text 'said' crosses the edges of ") and "'balloon'" in x for x in r["warnings"]), r


# -- warnings through the tools (report 8's labels, report 9's boxes) -------------------------------------
@pytest.mark.anyio
async def test_overlap_warnings_name_real_collisions_only(fresh_session):
    async with Client(server.mcp) as c:
        await c.call_tool("document_create", {"width": 200, "height": 120, "unit": "mm"})
        await c.call_tool("add_elements", {"elements": [
            {"type": "polyline", "id": "road", "points": [[10, 60], [190, 60]], "stroke": "#000", "stroke_width": 1},
            {"type": "rect", "id": "box", "x": 100, "y": 80, "width": 40, "height": 16, "fill": "#eef"}]})
        r = text(await c.call_tool("repeat", {"step": [0, 0], "template": [
            {"type": "text", "id": "t", "x": "{x}", "y": "{y}", "text": "{name}", "font_size": 5, "halo": "{h}"}],
            "rows": [{"name": "Alpha", "x": 20, "y": 30, "h": "none"}, {"name": "Beta", "x": 30, "y": 31, "h": "none"},
                     {"name": "Gamma", "x": 60, "y": 61, "h": "none"}, {"name": "Delta", "x": 100, "y": 61, "h": "#fff"},
                     {"name": "Inside", "x": 105, "y": 90, "h": "none"}, {"name": "Edge", "x": 135, "y": 90, "h": "none"}]}))
        w = r["warnings"]  # the overlap's size depends on the default font (Arial, DejaVu, Helvetica)
        assert len(w) == 3 and re.fullmatch(r"text 't-1' overlaps text 't-2' \(\d+\.\d x \d+\.\d\)\.", w[0])
        assert w[1:] == ["text 't-6' crosses the edge of 'box'.",
                         "text 't-3' is crossed by 'road' (give it a halo if that is intended)."]
        r = text(await c.call_tool("add_elements", {"elements": [
            {"type": "text", "id": f"pile{k}", "x": 0, "y": 0, "text": f"Label {k}"} for k in range(4)]}))
        assert r["warnings"] == ["4 elements are stacked on one spot (pile0, pile1, pile2, pile3): "
                                 "not checked against each other until arranged."]


# -- place (report 4) ---------------------------------------------------------------------------------
def test_place_below_measured_glyphs_and_follow(engine):
    doc = Document.create(100, 80, "mm")
    doc.add({"type": "text", "id": "big", "x": 50, "y": 30, "text": "Ag", "font_size": 16, "text_anchor": "middle"})
    doc.add({"type": "text", "id": "cap", "x": 0, "y": 0, "text": "caption", "font_size": 4,
             "place": {"below": "big", "gap": 2, "align": "center"}})
    r = engine.settle(doc, {"cap"})
    b = engine.bboxes(doc)
    assert b["cap"][1] == pytest.approx(b["big"][1] + b["big"][3] + 2, abs=0.01)  # below the descender of g
    assert b["cap"][0] + b["cap"][2] / 2 == pytest.approx(b["big"][0] + b["big"][2] / 2, abs=0.01)
    assert set(r["placed"]) == {"cap"}
    doc.update("big", {"font_size": 24})
    engine.settle(doc, {"big"})  # the reference changed: the caption follows
    b = engine.bboxes(doc)
    assert b["cap"][1] == pytest.approx(b["big"][1] + b["big"][3] + 2, abs=0.01)
    # after an explicit move of the caption itself (align/layout), only reference changes pull it back
    engine.translate(doc, {"cap": (0, 10)})
    assert engine.settle(doc, {"cap"}, deps_only=True) == {}
    doc.update("cap", {"place": {"right_of": "cap"}})
    with pytest.raises(DocumentError, match="itself"):
        engine.settle(doc, {"cap"})
    with pytest.raises(DocumentError, match="exactly one"):
        doc.update("cap", {"place": {"below": "big", "above": "big"}})


def test_place_and_fit_chain(engine):
    # a card: body placed below the title, the card rect fitted around both
    doc = Document.create(120, 80, "mm")
    doc.add({"type": "text", "id": "title", "x": 10, "y": 20, "text": "Title", "font_size": 6})
    doc.add({"type": "text", "id": "body", "x": 10, "y": 0, "text": "Body text", "font_size": 3,
             "place": {"below": "title", "gap": 1}})
    doc.add({"type": "rect", "id": "card", "fit_to": ["title", "body"], "fit_padding": 2, "fill": "none"})
    r = engine.settle(doc, {"title", "body", "card"})
    b = engine.bboxes(doc)
    assert b["card"][1] + b["card"][3] == pytest.approx(b["body"][1] + b["body"][3] + 2, abs=0.05)
    assert set(r) == {"placed", "fitted"}
    doc.update("title", {"text": "Title\nsecond line"})
    engine.settle(doc, {"title"})  # body moves down, then the card refits around both
    b = engine.bboxes(doc)
    assert b["body"][1] == pytest.approx(b["title"][1] + b["title"][3] + 1, abs=0.01)
    assert b["card"][1] + b["card"][3] == pytest.approx(b["body"][1] + b["body"][3] + 2, abs=0.05)


@pytest.mark.anyio
async def test_place_in_repeat_templates(fresh_session, engine):
    async with Client(server.mcp) as c:
        await c.call_tool("document_create", {"width": 150, "height": 80, "unit": "mm"})
        r = text(await c.call_tool("repeat", {"rows": [{"l": "அ"}, {"l": "இ"}, {"l": "ஔ"}], "step": [45, 0], "template": [
            {"type": "text", "id": "letter", "x": 20, "y": 30, "text": "{l}", "font_size": 16, "text_anchor": "middle",
             "font_family": "Nirmala UI"},
            {"type": "text", "id": "sound", "x": 20, "y": 0, "text": "{n}", "font_size": 5, "text_anchor": "middle",
             "place": {"below": "letter", "gap": 1.5}}]}))
        assert set(r["placed"]) == {"sound-1", "sound-2", "sound-3"}
    b = engine.bboxes(fresh_session.docs["doc1"])
    for k in (1, 2, 3):  # each 1.5 below its own glyph's real bottom (they differ per letter)
        assert b[f"sound-{k}"][1] == pytest.approx(b[f"letter-{k}"][1] + b[f"letter-{k}"][3] + 1.5, abs=0.01)


# -- layout anchors (report 10) --------------------------------------------------------------------------
def test_layout_by_anchor_aligns_frames(engine):
    doc = Document.create(210, 100, "mm")
    for k, label in ((1, "3"), (2, "0.001")):  # tick labels of different widths left of each frame
        doc.add({"type": "rect", "id": f"f{k}", "x": 10, "y": 10, "width": 50, "height": 30, "fill": "none",
                 "stroke": "#000", "stroke_width": 0.3})
        doc.add({"type": "text", "id": f"l{k}", "x": 8, "y": 20, "text": label, "font_size": 4, "text_anchor": "end"})
    engine.layout(doc, [{"ids": ["f1", "l1"], "anchor": "f1"}, {"ids": ["f2", "l2"], "anchor": "f2"}],
                  "row", 30, at=(20, 20))
    b = engine.bboxes(doc)
    assert b["f1"][:2] == pytest.approx((20, 20), abs=0.01)
    assert b["f2"][0] == pytest.approx(b["f1"][0] + b["f1"][2] + 30, abs=0.01)  # frame to frame, labels hang outside
    with pytest.raises(DocumentError, match="anchor"):
        engine.layout(doc, [{"ids": ["f1"], "anchor": "f1", "extra": 1}])
