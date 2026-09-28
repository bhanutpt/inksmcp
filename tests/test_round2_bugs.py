"""Bugs from field-test round 2 (D-021: fixed right away): reports 5 (comic), 7 (floor plan), 10 (datasheet)."""
import json

import pytest
from mcp import Client

from inksmcp import grids, server
from inksmcp.document import Document
from inksmcp.engine import Engine
from inksmcp.inkscape import InkscapeShell, ShellDied


@pytest.fixture
def fresh_session(engine, monkeypatch):
    s = server.Session()
    s._engine = engine
    monkeypatch.setattr(server, "session", s)
    return s


def text(r):
    return json.loads(r.content[0].text)


# -- report 10, bug 1: majors vanished when major was a rounded multiple of minor --------------
def test_linear_ticks_class_lines_by_index():
    t = grids.linear_ticks(70, major=11.6667, minor=2.3333, label_start=0, label_step=0.25)
    majors = [(p, lab) for p, c, lab in t if c == "major"]
    assert [lab for _, lab in majors] == ["0", "0.25", "0.5", "0.75", "1", "1.25", "1.5"]
    assert majors[1][0] == pytest.approx(11.6667)  # placed at fractions of major, as `plot` maps
    assert len(t) == 31 and t[-1][0] == 70  # a line within 0.01 % of the edge is on it


@pytest.mark.parametrize("spec, msg", [
    ({"major": 10, "minor": 3}, "major: 10 is not a whole multiple of 3"),
    ({"major": 10, "medium": 5, "minor": 2}, "medium: 5 is not a whole multiple of 2"),
    ({"major": 10, "medium": 4, "minor": 2}, "major: 10 is not a whole multiple of medium 4"),
])
def test_linear_spacings_that_do_not_nest_are_errors(spec, msg):
    with pytest.raises(ValueError, match=msg):
        grids.axis_ticks({"scale": "linear", **spec}, 100)


def test_plot_on_a_rounded_grid_edge_does_not_warn(engine):
    doc = Document.create(120, 100, "mm")
    r = engine.grid(doc, [30, 20, 70, 60], {"scale": "linear", "major": 11.6667, "minor": 2.3333},
                    {"scale": "linear", "major": 12, "minor": 2.4})
    assert r["lines"]["major"] == 5 + 4  # interior x and y majors (edges are the border)
    out = engine.plot(doc, "grid", [{"points": [[0, 0], [6, 5]]}])  # 6 * 11.6667 = 70.0002
    assert "warnings" not in out


# -- report 10, bug 2: log labels ignored `start` ------------------------------------------------
def test_log_labels_follow_start():
    t = grids.axis_ticks({"scale": "log", "cycles": 5, "start": 10, "subdivisions": "integers"}, 72)
    assert [(round(p, 3), lab) for p, _, lab in t if lab] == [
        (0, "10"), (14.4, "100"), (28.8, "1000"), (43.2, "10000"), (57.6, "100000"), (72, "1000000")]
    t = grids.axis_ticks({"scale": "log", "cycles": 4, "start": 0.001}, 40)
    assert [lab for _, _, lab in t if lab] == ["0.001", "0.01", "0.1", "1", "10"]
    paper = grids.axis_ticks({"scale": "log", "cycles": 2, "start": 10, "labels": "paper"}, 40)
    assert [lab for _, _, lab in paper if lab][:3] == ["1", "2", "3"]  # printed log paper, on request
    with pytest.raises(ValueError, match="paper"):
        grids.axis_ticks({"scale": "log", "cycles": 2, "labels": "si"}, 40)


# -- report 7: path_operation result id --------------------------------------------------------
@pytest.mark.anyio
async def test_path_operation_names_the_result(fresh_session):
    async with Client(server.mcp) as c:
        await c.call_tool("document_create", {"width": 100, "height": 60, "unit": "mm"})
        await c.call_tool("add_elements", {"elements": [
            {"type": "rect", "id": f"{p}{k}", "x": 10 + 12 * k, "y": 10 + 30 * (p == "o"), "width": 30,
             "height": 20} for p in "wo" for k in range(3)]})
        r = text(await c.call_tool("path_operation", {"operation": "union", "ids": ["w2", "w0", "w1"]}))
        assert r["result"] == ["w0"]  # union keeps the bottom id (S2)
        r = text(await c.call_tool("path_operation", {"operation": "combine", "ids": ["o0", "o1", "o2"]}))
        assert r["result"] == ["o2"]  # combine keeps the TOP id (E22)
        r = text(await c.call_tool("path_operation", {"operation": "difference", "ids": ["w0", "o2"]}))
        assert r["result"] == ["w0"] and r["removed"] == ["o2"]


# -- report 5: shell crash left add_elements half-applied -----------------------------------------
def test_a_pass_is_retried_when_the_shell_dies():
    eng = Engine(InkscapeShell())
    real_run, died = eng.shell.run, []

    def dying_run(command, check=True):
        if command == "query-all" and not died:
            died.append(command)
            real_run("quit")  # the process exits mid-pass
        return real_run(command, check)

    try:
        eng.shell.run = dying_run
        doc = Document.create(50, 50, "mm")
        doc.add({"type": "rect", "id": "r", "x": 10, "y": 10, "width": 20, "height": 20})
        assert eng.bboxes(doc)["r"] == pytest.approx((10, 10, 20, 20), abs=0.01)
        assert died and eng.shell.restarts == 1
    finally:
        eng.close()


def test_shell_death_says_what_it_was_running():
    with InkscapeShell() as sh:
        with pytest.raises(ShellDied, match=r"exit code \d+\) while running 'quit'"):
            sh.run("quit")
        assert sh.run("action-list").output  # the next command starts a fresh shell


@pytest.mark.anyio
async def test_failed_tools_leave_the_document_unchanged(fresh_session, engine, monkeypatch):
    def crash(*a, **k):
        raise ShellDied("Inkscape shell exited unexpectedly (test)")

    async with Client(server.mcp) as c:
        await c.call_tool("document_create", {"width": 100, "height": 60, "unit": "mm"})
        await c.call_tool("add_elements", {"elements": [{"type": "rect", "id": "keep", "x": 1, "y": 1,
                                                         "width": 5, "height": 5}]})
        monkeypatch.setattr(engine, "wrap_texts", crash)
        r = await c.call_tool("add_elements", {"elements": [
            {"type": "rect", "id": "box", "x": 10, "y": 10, "width": 30, "height": 20},
            {"type": "text", "id": "note", "x": 10, "y": 40, "text": "wrap me please", "width": 20}]})
        assert r.is_error and "Nothing was changed" in r.content[0].text
        r = await c.call_tool("update_elements", {"updates": [{"id": "keep", "x": 50},
                                                              {"id": "keep", "text": "x", "width": 9}]})
        assert r.is_error
        monkeypatch.undo()
        doc = fresh_session.docs["doc1"]
        assert "box" not in doc.ids() and "note" not in doc.ids()
        assert doc.get("keep").get("x") == "1"
