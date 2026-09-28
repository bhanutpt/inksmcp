"""`repeat` — template stamping with alternate mirroring (field report 3, E21)."""
import json

import pytest
from mcp import Client

from inksmcp import server, templates
from inksmcp.document import Document

ROWS = [{"year": "1903", "title": "First flight", "desc": "The Wright Flyer stays aloft for 12 seconds."},
        {"year": "1927", "title": "Atlantic solo", "desc": "Lindbergh flies New York to Paris non-stop."},
        {"year": "1947", "title": "Sound barrier", "desc": "The Bell X-1 passes Mach 1 over the desert."}]
TEMPLATE = [
    {"type": "polygon", "id": "ptr", "points": [[92, 24], [98, 30], [92, 36]], "fill": "#ddd"},
    {"type": "circle", "id": "badge", "cx": 105, "cy": 30, "r": 5, "fill": "#0f2742"},
    {"type": "group", "id": "card"},
    {"type": "rect", "id": "box", "parent": "card", "x": 15, "y": 18, "width": 77, "height": 26, "fill": "#eee"},
    {"type": "text", "id": "year", "parent": "card", "x": 19, "y": 22, "vertical_anchor": "top", "text": "{year}",
     "font_size": 7},
    {"type": "text", "id": "title", "parent": "card", "x": 41, "y": 27, "text": "{title}", "font_size": 4},
    {"type": "text", "id": "desc", "parent": "card", "x": 19, "y": 34, "text": "{desc}", "font_size": 3.2,
     "width": 69}]


def test_fill_and_stamp_are_pure():
    ctx = {"w": 12.5, "name": "A", "i": 0, "n": 1}
    assert templates.fill({"width": "{w}", "text": "{name}: {w} {{x}}", "pts": [["{w}", 1]]}, ctx) == \
        {"width": 12.5, "text": "A: 12.5 {x}", "pts": [[12.5, 1]]}
    with pytest.raises(ValueError, match="placeholder {nope}"):
        templates.fill("{nope}", ctx)
    rows = templates.stamp([{"type": "group", "id": "g"}, {"type": "rect", "id": "r", "parent": "g"},
                            {"type": "text", "id": "t{n}x", "text": "{n}"}, {"type": "circle"}], [{}, {}])
    name, spec, mode = rows[1][1]
    assert (name, spec["id"], spec["parent"], mode) == ("r", "r-2", "g-2", "none")  # children move with parent
    assert rows[1][2][1]["id"] == "t2x" and rows[1][2][1]["text"] == 2 and rows[1][2][2] == "block"
    assert rows[0][3][0] == "#3" and "id" not in rows[0][3][1] and rows[0][3][2] == "reflect"
    for bad, msg in (([{"type": "rect", "layer": "L"}], "layer"), ([{"type": "rect", "parent": "zz"}], "parent"),
                     ([{"type": "rect", "mirror": "flip"}], "mirror")):
        with pytest.raises(ValueError, match=msg):
            templates.stamp(bad, [{}])
    with pytest.raises(ValueError, match="reserved"):
        templates.stamp([{"type": "rect"}], [{"n": 3}])
    assert templates.offset(4, [10, 20], 3) == (10, 20) and templates.offset(2, [0, 34], None) == (0, 68)


def test_vertical_anchor_inside_transformed_group(engine):
    # E21: anchoring compared the local y with document-space caps -> off by the group's translate
    doc = Document.create(100, 100, "mm")
    doc.add({"type": "group", "id": "g", "transform": "translate(0,30)"})
    doc.add({"type": "text", "id": "t", "parent": "g", "x": 10, "y": 10, "text": "H", "font_size": 10})
    engine.anchor_texts(doc, {"t": ("top", 10)})
    assert engine.bboxes(doc)["t"][1] == pytest.approx(40, abs=0.1)


@pytest.mark.anyio
async def test_repeat_timeline_with_mirroring(engine, monkeypatch):
    s = server.Session()
    s._engine = engine
    monkeypatch.setattr(server, "session", s)
    async with Client(server.mcp) as c:
        async def call(name, ok=True, **args):
            r = await c.call_tool(name, args)
            assert r.is_error != ok, r.content
            return json.loads(r.content[0].text) if ok else r.content[0].text

        await call("document_create", width=210, height=120, unit="mm")
        r = await call("repeat", template=TEMPLATE, rows=ROWS, step=[0, 34], mirror={"x": 105}, id_prefix="entry")
        assert r["groups"] == ["entry-1..entry-3"]  # runs are shortened (field report 6)
        assert r["ids"]["year"] == ["year-1..year-3"] and set(r["wrapped_lines"]) == {"desc-1", "desc-2", "desc-3"}
        doc = s.docs["doc1"]
        assert "".join(doc.get("year-2").itertext()) == "1927"
        b = engine.bboxes(doc)
        # row 1 as drawn, row 2 mirrored about x = 105 and 34 lower, row 3 as drawn again
        assert b["ptr-1"][0] == pytest.approx(92, abs=0.05) and b["ptr-3"][1] == pytest.approx(24 + 68, abs=0.05)
        assert b["ptr-2"][0] == pytest.approx(112, abs=0.05) and b["ptr-2"][1] == pytest.approx(58, abs=0.05)
        assert b["badge-2"][0] == pytest.approx(100, abs=0.05)
        assert b["box-2"][0] == pytest.approx(210 - 15 - 77, abs=0.05)  # the card crossed the axis
        # texts kept their reading direction and their place inside the card
        assert b["year-2"][0] - b["box-2"][0] == pytest.approx(b["year-1"][0] - b["box-1"][0], abs=0.05)
        assert b["year-2"][1] == pytest.approx(b["year-1"][1] + 34, abs=0.05)
        assert b["year-1"][1] == pytest.approx(22, abs=0.1)  # vertical_anchor top inside a row group
        # a grid of legend entries: offsets by column/row, off-page rows reported
        r = await call("repeat", template=[{"type": "rect", "id": "sw", "x": 10, "y": 100, "width": 4, "height": 4,
                                            "fill": "{c}"}], rows=[{"c": "#f00"}, {"c": "#0f0"}, {"c": "#00f"}],
                       step=[30, 18], columns=2, id_prefix="legend")
        b = engine.bboxes(doc)
        assert b["sw-2"][:2] == pytest.approx((40, 100), abs=0.05) and b["sw-3"][:2] == pytest.approx((10, 118), abs=0.05)
        assert "'legend-3' extends beyond the page" in r["warnings"][0]
        # step 2 check: the swatch really lands on the third card's description
        assert r["warnings"][1:] == ["text 'desc-3' crosses the edge of 'sw-2'."]
        # all or nothing: sw-1 exists already, so no row of this call may stay behind
        before = len(list(doc.root.iter()))
        err = await call("repeat", ok=False, template=[{"type": "rect", "id": "sw"}], rows=[{}], step=[0, 0],
                         id_prefix="again")
        assert "already exists" in err and len(list(doc.root.iter())) == before
