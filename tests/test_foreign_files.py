"""Editing SVGs someone else made (field report 2026-09-28-edit-existing-svgs, E30, D-030)."""
import gzip
import json

import pytest
from mcp import Client

from inksmcp import server
from inksmcp.document import Document, norm_color


@pytest.fixture
def fresh_session(engine, monkeypatch):
    s = server.Session()
    s._engine = engine
    monkeypatch.setattr(server, "session", s)
    return s


def ok(r):
    assert not r.is_error, r.content
    return json.loads(r.content[0].text)


def err(r):
    assert r.is_error
    return r.content[0].text


SVG = 'xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"'
LIBRARY = f"""<svg {SVG} width="100" height="50" style="fill:black;stroke:black">
  <defs><linearGradient id="g"><stop offset="0" stop-color="#f00"/></linearGradient>
    <symbol id="Parking" viewBox="0 0 10 10"><title>Parking</title><rect x="1" y="1" width="8" height="8" fill="none"/></symbol>
    <symbol id="Water" viewBox="0 0 10 10"><title>Water</title><circle cx="5" cy="5" r="4" fill="url(#g)"/></symbol></defs>
  <use xlink:href="#Parking" x="0" y="0" width="20" height="20"/><use xlink:href="#Water" x="30" y="0" width="20" height="20"/>
</svg>"""


def test_norm_color():
    assert norm_color("rgb(153,204,50)") == norm_color("#99CC32") == norm_color("#99cc32") == "#99cc32"
    assert norm_color("#abc") == "#aabbcc" and norm_color("black") == "#000000" and norm_color("rgb(100%,0%,0%)") == "#ff0000"


@pytest.mark.anyio
async def test_open_svgz_and_letterboxed_pages(fresh_session, tmp_path):
    # a viewBox narrower than the page (drawn centred, meet) and not starting at 0,0; root paint; .svgz
    src = f"""<svg {SVG} width="200" height="100" viewBox="10 0 100 100" stroke="#00f">
      <rect id="r" x="10" y="0" width="100" height="100" fill="#c00"/></svg>"""
    (tmp_path / "a.svgz").write_bytes(gzip.compress(src.encode()))
    async with Client(server.mcp) as c:
        r = ok(await c.call_tool("document_open", {"path": str(tmp_path / "a.svgz")}))
        assert r["page"]["width"] == 200 and r["page"]["unit"] == "px"
        assert any(n.startswith("Page normalised, rendering unchanged") for n in r["notes"])
        assert any("stroke:#00f" in n for n in r["notes"])
        box = ok(await c.call_tool("inspect", {}))["outline"][0]
        assert box["id"] == "r" and box["stroke"] == "#00f"
        assert box["bbox"] == pytest.approx([49.5, -0.5, 101, 101], abs=0.01)  # measured where it renders
        # new elements don't inherit the root's stroke
        ok(await c.call_tool("add_elements", {"elements": [{"type": "rect", "id": "n", "x": 0, "y": 0, "width": 10,
                                                            "height": 10, "fill": "#0c0"}]}))
        n = ok(await c.call_tool("inspect", {"find": {"id_prefix": "n"}}))["found"][0]
        assert "stroke" not in n and n["bbox"] == [0, 0, 10, 10]
        saved = ok(await c.call_tool("document_save", {"path": str(tmp_path / "b.svgz")}))
        assert gzip.decompress((tmp_path / "b.svgz").read_bytes()).count(b'sodipodi:docname="b.svgz"') == 1
        assert saved["saved"].endswith("b.svgz")
        # % width (read as the viewBox width, as Inkscape does) + mm height: one uniform scale
        (tmp_path / "t.svg").write_text(f'<svg {SVG} width="100%" height="297mm" viewBox="0 0 594 840">'
                                        '<rect id="t" x="0" y="0" width="594" height="840" fill="#ccc"/></svg>')
        r = ok(await c.call_tool("document_open", {"path": str(tmp_path / "t.svg")}))
        assert r["page"]["width"] == 594 and r["page"]["height"] == pytest.approx(1122.52, abs=0.01)
        b = ok(await c.call_tool("inspect", {}))["outline"][0]["bbox"]
        assert b == pytest.approx([0, 141.26, 594, 840], abs=0.01)
        # no viewBox: user units are px, whatever the width's unit
        (tmp_path / "f.svg").write_text(f'<svg {SVG} width="210mm" height="297mm"><rect id="q" width="140" height="10"/>'
                                        '<flowRoot id="fr"><flowRegion><rect width="50" height="50"/></flowRegion>'
                                        '<flowPara>Flowed words</flowPara></flowRoot></svg>')
        r = ok(await c.call_tool("document_open", {"path": str(tmp_path / "f.svg")}))
        assert r["page"]["unit"] == "px"
        assert {"id": "fr", "type": "flowtext"}.items() <= r["outline"][1].items() and r["outline"][1]["text"] == "Flowed words"
        # not an SVG: a message, never an empty error
        (tmp_path / "x.svg").write_bytes(b"\x00\x01 not xml")
        assert "is not a readable SVG file" in err(await c.call_tool("document_open", {"path": str(tmp_path / "x.svg")}))


def test_stretched_page_keeps_its_shape(engine):
    doc = Document.from_bytes(f'<svg {SVG} width="200" height="100" viewBox="0 0 100 100" preserveAspectRatio="none">'
                              '<rect id="r" x="0" y="0" width="100" height="100"/></svg>'.encode())
    notes = doc.normalise()
    assert "stretched" in notes[0] and doc.viewbox == (0, 0, 100, 50)  # x keeps its scale: 2 px per unit
    assert doc.px_per_user_unit == 2 and engine.bboxes(doc)["r"] == pytest.approx((0, 0, 100, 50), abs=0.01)


@pytest.mark.anyio
async def test_find_by_colour_and_symbols(fresh_session, tmp_path):
    (tmp_path / "tiger.svg").write_text(f"""<svg {SVG} width="100" height="100" viewBox="0 0 100 100" fill="none">
      <g id="g"><path id="eye1" fill="rgb(153,204,50)" d="M 10 10 h 5 v 5 z"/><path id="eye2" style="fill:#99CC32" d="M 30 10 h 5 v 5 z"/>
      <path id="fur" fill="#f90" d="M 0 50 h 50 v 50 z"/><text id="t" x="5" y="90" fill="#000">Tiger total</text></g></svg>""")
    (tmp_path / "lib.svg").write_text(LIBRARY)
    async with Client(server.mcp) as c:
        ok(await c.call_tool("document_open", {"path": str(tmp_path / "tiger.svg")}))
        r = ok(await c.call_tool("inspect", {"find": {"fill": "#99cc32"}}))
        assert [f["id"] for f in r["found"]] == ["eye1", "eye2"] and r["found"][0]["fill"] == "rgb(153,204,50)"
        r = ok(await c.call_tool("inspect", {"find": {"type": "text", "text": "TOTAL"}, "bbox": False}))
        assert [f["id"] for f in r["found"]] == ["t"]
        assert "unknown" in err(await c.call_tool("inspect", {"find": {"colour": "red"}}))
        ok(await c.call_tool("document_open", {"path": str(tmp_path / "lib.svg")}))
        r = ok(await c.call_tool("inspect", {"find": {"type": "symbol"}, "bbox": False}))
        assert [(f["id"], f["title"]) for f in r["found"]] == [("Parking", "Parking"), ("Water", "Water")]
        uses = ok(await c.call_tool("inspect", {"find": {"type": "use"}, "bbox": False}))["found"]
        assert [(u["href"], u["stroke"]) for u in uses] == [("Parking", "black"), ("Water", "black")]


@pytest.mark.anyio
async def test_import_and_use_library_symbols(fresh_session, tmp_path):
    (tmp_path / "lib.svg").write_text(LIBRARY)
    opened = Document.open(tmp_path / "lib.svg")
    first_use = next(e.get("id") for e in opened.root.iter() if isinstance(e.tag, str) and e.tag.endswith("}use"))
    async with Client(server.mcp) as c:
        ok(await c.call_tool("document_create", {"width": 100, "height": 80, "unit": "mm"}))
        ok(await c.call_tool("document_save", {"path": str(tmp_path / "sheet.svg")}))  # relative paths start here
        r = ok(await c.call_tool("import_file", {"path": str(tmp_path / "lib.svg"), "id": "lib"}))
        assert r["scale"][0] == r["scale"][1]
        found = ok(await c.call_tool("inspect", {"find": {"id_prefix": first_use}, "bbox": False}))["found"]
        assert found[0]["href"] == "Parking" and found[0]["stroke"] == "black"  # same id as document_open; root paint kept
        d = ok(await c.call_tool("delete_elements", {"ids": ["lib"]}))
        assert d["defs_removed"] == 3  # both symbols and the gradient only Water used
        # place symbols straight from the library file, twice: one copy in defs, the library's paint applied
        r = ok(await c.call_tool("add_elements", {"elements": [
            {"type": "use", "id": "p1", "href": "lib.svg#Parking", "x": 10, "y": 10, "width": 10, "height": 10},
            {"type": "use", "id": "p2", "href": f"{tmp_path / 'lib.svg'}#Parking", "x": 30, "y": 10, "width": 10, "height": 10},
            {"type": "use", "id": "w1", "href": "lib.svg#Water", "x": 50, "y": 10, "width": 10, "height": 10}]}))
        doc = fresh_session.docs[fresh_session.current]
        assert len(doc.find({"type": "symbol"})) == 2
        p1 = doc.describe(doc.get("p1"))
        assert p1["href"] == "Parking" and p1["stroke"] == "black"
        box = ok(await c.call_tool("inspect", {"find": {"id_prefix": "p1"}}))["found"][0]["bbox"]
        assert box[2] == pytest.approx(9, abs=0.01)  # the 8/10 rect scaled to 10 mm, plus its 1-unit stroke (1 mm)
        assert "has no element 'Nope'" in err(await c.call_tool("add_elements", {"elements": [
            {"type": "use", "href": "lib.svg#Nope"}]}))


@pytest.mark.anyio
async def test_clearer_messages(fresh_session, monkeypatch):
    async with Client(server.mcp) as c:
        ok(await c.call_tool("document_create", {"width": 100, "height": 80, "unit": "mm"}))
        e = err(await c.call_tool("add_elements", {"defaults": {"type": "text", "font_size": 4},
                                                   "elements": [{"id": "a", "text": "x"}]}))
        assert "defaults can't set 'type'" in e
        r = ok(await c.call_tool("add_elements", {"elements": [
            {"type": "rect", "id": "box", "x": 10, "y": 10, "width": 30, "height": 10, "fill": "#eee"},
            {"type": "rect", "id": "under", "x": 0, "y": 0, "width": 30, "height": 5, "fill": "#ccc",
             "place": {"below": "box", "gap": 2}}]}))
        assert r["placed"]["under"] == pytest.approx([0, 22, 30, 5], abs=0.01)  # its box as inspect reports it
        monkeypatch.setattr(Document, "outline", lambda *a, **k: {}["boom"])
        assert "Unexpected KeyError: 'boom'" in err(await c.call_tool("inspect", {"bbox": False}))
