"""Fixes and features from docs/field-reports/2026-09-27-log-graph-a4.md (E15)."""
import json
import math

import pytest
from mcp import Client

from inksmcp import grids, server
from inksmcp.document import Document, DocumentError
from inksmcp.inkscape import InkscapeError

from .conftest import png_size

LABEL = "{http://www.inkscape.org/namespaces/inkscape}label"


# -- grid maths ------------------------------------------------------------------
def test_log_ticks_match_stationery_log_paper():
    t = grids.log_ticks(171, 3)
    per_class = {c: sum(1 for _, k, _ in t if k == c) for c in grids.CLASSES}
    assert per_class == {"major": 4, "medium": 24, "minor": 78}  # per cycle: 1 decade, 8 integers, 26 subdivisions
    assert [lab for _, _, lab in t if lab][:10] == ["1", "2", "3", "4", "5", "6", "7", "8", "9", "1"]
    two = next(p for p, _, lab in t if lab == "2")
    assert two == pytest.approx(math.log10(2) * 57)
    assert t[-1] == (171, "major", "1")


def test_linear_ticks():
    t = grids.linear_ticks(20, major=10, medium=5, minor=1, label_start=100, label_step=50)
    assert len(t) == 21
    assert [(p, lab) for p, c, lab in t if c == "major"] == [(0, "100"), (10, "150"), (20, "200")]
    assert [p for p, c, _ in t if c == "medium"] == [5, 15]
    with pytest.raises(ValueError, match="5000"):
        grids.linear_ticks(1000, major=10, minor=0.1)
    with pytest.raises(ValueError, match="unknown keys"):
        grids.axis_ticks({"scale": "log", "cycles": 2, "major": 1}, 10)


# -- export / preview (bug 1 and 2 of the report) --------------------------------
@pytest.fixture
def three():
    doc = Document.create(100, 50, "mm", background="#ffffff")
    doc.add({"type": "rect", "id": "a", "x": 10, "y": 10, "width": 20, "height": 20, "fill": "#ff0000"})
    doc.add({"type": "rect", "id": "b", "x": 60, "y": 20, "width": 20, "height": 20, "fill": "#0000ff"})
    doc.add({"type": "circle", "id": "c", "cx": 50, "cy": 25, "r": 5, "fill": "#00ff00"})
    return doc


def test_export_id_takes_one_id_and_unknown_ids_now_raise(shell, tmp_path):
    # E15: "export-id:a,b" looks for one object named "a,b" and only warns "... was not found".
    svg = tmp_path / "x.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect id="a" width="5" height="5"/></svg>')
    shell.run(f"file-open:{svg}")
    try:
        with pytest.raises(InkscapeError, match="not found"):
            shell.run(f"export-id:a,b;export-id-only:true;export-filename:{tmp_path / 'o.png'};export-type:png;export-do")
    finally:
        shell.run("file-close", check=False)


def test_multi_id_export_and_preview(engine, three, tmp_path):
    out = engine.export(three, tmp_path / "ab.png", ids=["a", "b"], dpi=96)
    assert png_size(out.read_bytes()) == (265, 113)  # union of a and b: 70 x 30 mm
    iso = engine._isolated(three, ["a", "b"])
    assert "display:none" in iso.get("c").get("style") and "display:none" not in (iso.get("a").get("style") or "")
    assert png_size(engine.render_png(three, max_size=300, ids=["a", "b"])) == (300, 129)


def test_region_export_is_in_user_units(engine, three, tmp_path):
    # E15: export-area takes px; we convert from user units (mm here).
    out = engine.export(three, tmp_path / "r.png", region=(10, 10, 20, 10), dpi=96)
    assert png_size(out.read_bytes()) == (76, 38)
    with pytest.raises(DocumentError, match="region"):
        engine.export(three, tmp_path / "bad.png", region=(0, 0, 0, 5))


# -- vertical_anchor ----------------------------------------------------------------
def test_vertical_anchor_middle_and_top(engine):
    doc = Document.create(100, 100, "mm")
    doc.add({"type": "text", "id": "m", "x": 10, "y": 50, "text": "Hg", "font_size": 5})
    doc.add({"type": "text", "id": "t", "x": 40, "y": 50, "text": "Hg", "font_size": 5})
    engine.anchor_texts(doc, {"m": ("middle", 50), "t": ("top", 50)})
    _, caps = engine.measure(doc, ["m", "t"])
    assert caps["m"][1] + caps["m"][3] / 2 == pytest.approx(50, abs=0.01)
    assert caps["t"][1] == pytest.approx(50, abs=0.01)
    with pytest.raises(DocumentError, match="vertical_anchor"):
        doc.add({"type": "text", "x": 0, "y": 0, "text": "x", "vertical_anchor": "center"})


# -- grid against Inkscape -----------------------------------------------------------
def test_log_log_grid_a4(engine):
    doc = Document.create(210, 297, "mm", background="#ffffff")
    r = engine.grid(doc, [24, 15, 171, 260], {"scale": "log", "cycles": 3}, {"scale": "log", "cycles": 5},
                    color="#2a8a4a", labels={"sides": ["left", "bottom"]})
    # border replaces the outer decade lines: 3x5 cycles -> x majors 2, y majors 4
    assert r["lines"] == {"minor": 26 * 8, "medium": 8 * 8, "major": 2 + 4}
    assert r["labels"] == (9 * 5 + 1) + (9 * 3 + 1)  # 1..9 per cycle + closing 1, left and bottom
    assert [l.get(LABEL) for l in doc.layers()] == ["Grid minor", "Grid medium", "Grid major", "Grid labels"]
    labels = [c.get("id") for c in doc.layer("Grid labels")]
    _, caps = engine.measure(doc, labels)
    left_2 = next(i for i in labels if doc.get(i).text == "2" and doc.get(i).get("style").find("end") > 0)
    y_line = 15 + 260 - math.log10(2) * 52  # first cycle, from the bottom
    assert caps[left_2][1] + caps[left_2][3] / 2 == pytest.approx(y_line, abs=0.02)
    bottom = [i for i in labels if "middle" in doc.get(i).get("style")]
    assert {round(caps[i][1], 2) for i in bottom} == {round(15 + 260 + 1.2, 2)}  # cap tops on one line


def test_grid_errors(engine):
    doc = Document.create(100, 100)
    with pytest.raises(DocumentError, match="rect"):
        engine.grid(doc, [0, 0, 0, 10], {"scale": "linear", "major": 10}, None)
    with pytest.raises(DocumentError, match="major"):
        engine.grid(doc, [0, 0, 10, 10], {"scale": "linear"}, None)
    with pytest.raises(DocumentError, match="side"):
        engine.grid(doc, [0, 0, 10, 10], {"scale": "linear", "major": 5}, None, labels={"sides": ["inside"]})


# -- MCP tools ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_tools_from_field_report(engine, monkeypatch):
    s = server.Session()
    s._engine = engine
    monkeypatch.setattr(server, "session", s)
    async with Client(server.mcp) as c:
        async def call(name, **args):
            r = await c.call_tool(name, args)
            assert not r.is_error, r.content
            return r

        await call("document_create", width=210, height=297, unit="mm", background="#ffffff")
        r = await call("grid", rect=[20, 20, 170, 250], x={"scale": "linear", "major": 10, "medium": 5, "minor": 1},
                       y={"scale": "linear", "major": 10, "medium": 5, "minor": 1}, color="#e07020")
        data = json.loads(r.content[0].text)
        assert data["lines"]["major"] == 16 + 24 and set(data["ids"]) == {"minor", "medium", "major", "border"}
        r = await call("add_elements", defaults={"font_size": 3, "fill": "#333", "layer": "Notes"},
                       elements=[{"type": "text", "id": "n1", "x": 20, "y": 10, "text": "Name:",
                                  "vertical_anchor": "middle"},
                                 {"type": "line", "x1": 35, "y1": 11, "x2": 100, "y2": 11}])
        assert "font-size" not in (s.docs["doc1"].get(json.loads(r.content[0].text)["ids"][1]).get("style"))
        r = await c.call_tool("add_elements", {"defaults": {"font_size": 3}, "elements": [{"type": "rect"}]})
        assert r.is_error and "defaults" in r.content[0].text
        r = await call("render_preview", region=[15, 15, 40, 30], max_size=400)
        assert r.content[0].type == "image"
        r = await call("render_preview", ids=["n1", "grid-border"], max_size=300)
        assert r.content[0].type == "image"
