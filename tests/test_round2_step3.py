"""Round-2 build step 3 (D-024, D-028): grid cells in `repeat`, the `split` tool (E28)."""
import json

import pytest
from mcp import Client

from inksmcp import layout, server, templates


@pytest.fixture
def fresh_session(engine, monkeypatch):
    s = server.Session()
    s._engine = engine
    monkeypatch.setattr(server, "session", s)
    return s


def text(r):
    assert not r.is_error, r.content
    return json.loads(r.content[0].text)


def test_split_maths():
    cells = layout.split((10, 20, 190, 100), [[2, 1], 3], [3, 1], (4, 6))
    assert cells[0] == [(10, 20, 124, 70.5), (138, 20, 62, 70.5)]  # 190 - 4 = 186 -> 124 + 62; (100 - 6) * 3/4
    assert [c[0] for c in cells[1]] == [10, pytest.approx(74.6667, abs=1e-4), pytest.approx(139.3333, abs=1e-4)]
    assert cells[1][0][1] == pytest.approx(96.5)
    with pytest.raises(ValueError, match="ratios"):
        layout.split((0, 0, 10, 10), [[1, 0]], None, (0, 0))
    with pytest.raises(ValueError, match="one positive ratio per row"):
        layout.split((0, 0, 10, 10), [1, 1], [1], (0, 0))


def test_cell_offsets():
    assert templates.cell_offset({"col": 18, "row": 1}, 0, ["col", "row"], [22, 24]) == (374, 0)
    assert templates.cell_offset({"c": 3, "r": 9.5}, 0, ["c", "r"], [22, 24]) == (44, 204)
    with pytest.raises(ValueError, match="rows\\[4\\]: cell needs a number in 'row'"):
        templates.cell_offset({"col": 1}, 4, ["col", "row"], [1, 1])


@pytest.mark.anyio
async def test_split_and_cells_through_the_tools(fresh_session, engine):
    async with Client(server.mcp) as c:
        await c.call_tool("document_create", {"width": 210, "height": 297, "unit": "mm"})
        r = text(await c.call_tool("split", {"rows": [[2, 1], [1, 1], [1, 2]], "margin": [24, 10, 10, 10],
                                             "gutter": 4, "id_prefix": "panel", "style": {"stroke": "#000"}}))
        assert r["rows"] == [["panel-1", "panel-2"], ["panel-3", "panel-4"], ["panel-5", "panel-6"]]
        assert r["cells"]["panel-2"] == pytest.approx([138, 24, 62, 85], abs=1e-3)  # (297 - 34 - 2 * 4) / 3
        r = text(await c.call_tool("split", {"region": "panel-1", "rows": [4], "id_prefix": "strip"}))
        assert r["rows"] == [["strip-1..strip-4"]] and r["cells"]["strip-4"][2] == pytest.approx(125 / 4, abs=0.05)  # visual box: 124 + the 1 mm default stroke
        r = text(await c.call_tool("repeat", {"cell": ["col", "row"], "step": [22, 24], "rows": [
            {"s": "H", "col": 1, "row": 1}, {"s": "He", "col": 18, "row": 1}, {"s": "La", "col": 3, "row": 9.5}],
            "template": [{"type": "rect", "id": "box", "x": 10, "y": 30, "width": 20, "height": 22}]}))
        assert r["groups"] == ["row-1..row-3"]
        bad = await c.call_tool("repeat", {"cell": ["col", "row"], "columns": 3, "step": [1, 1], "rows": [{}],
                                           "template": [{"type": "rect"}]})
        assert bad.is_error and "no columns" in bad.content[0].text
    b = engine.bboxes(fresh_session.docs["doc1"])
    assert b["box-2"][:2] == pytest.approx((384, 30), abs=0.01) and b["box-3"][:2] == pytest.approx((54, 234), abs=0.01)
