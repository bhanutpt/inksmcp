"""Cheap follow-ups from docs/field-reports/2026-09-27-flight-infographic.md (E19)."""
import pytest

from inksmcp.document import Document, DocumentError, parse_style


def bar_chart(engine):
    doc = Document.create(200, 90, "mm")
    r = engine.grid(doc, [50, 10, 140, 60], {"scale": "linear", "major": 28, "minor": 5.6, "label_step": 500},
                    {"scale": "linear", "major": 12, "lines": False}, border=0,
                    labels={"sides": ["bottom"], "bold_major": False}, id_prefix="speed")
    return doc, r


def test_grid_axis_without_lines(engine):
    # field report 3: vertical gridlines only; the y axis still maps data for plot
    doc, r = bar_chart(engine)
    assert r["lines"] == {"minor": 20, "medium": 0, "major": 6}  # x only: 0..140 every 5.6 / 28
    assert "V" in doc.get("speed-major").get("d") and "H" not in doc.get("speed-major").get("d")
    labels = [e for e in doc.root.iter() if isinstance(e.tag, str) and (e.get("id") or "").startswith("speed-label")]
    assert labels and all("font-weight" not in parse_style(e.get("style")) for e in labels)
    p = engine.plot(doc, "speed", [{"points": [[0, 2.5], [1000, 2.5]], "marker": "none"}])
    assert sum(p["series"][0]["points"], []) == pytest.approx([50, 40, 106, 40])


def test_plot_ids_follow_series_id_and_label_options(engine):
    doc, _ = bar_chart(engine)
    r = engine.plot(doc, "speed", [
        {"id": "bar_x1", "points": [[0, 1.5], [1127, 1.5]], "stroke_width": 7, "marker": "none",
         "point_labels": [None, "1,127 km/h"], "label_offset": [2, 0]},
        {"id": "bar_concorde", "points": [[0, 0.5], [2179, 0.5]], "stroke_width": 7,
         "point_labels": [None, "2,179 km/h"], "label_offset": [-2, 0], "label_color": "#ffffff",
         "label_halo": "none", "label_anchor": "end"}])
    x1, conc = r["series"]
    assert x1["line"] == "bar_x1-line" and x1["labels"] == ["bar_x1-label-2"]
    assert conc["markers"] == ["bar_concorde-marker-1", "bar_concorde-marker-2"]
    assert parse_style(doc.get("bar_x1-label-2").get("style"))["stroke"] == "#ffffff"  # default halo
    st = parse_style(doc.get("bar_concorde-label-2").get("style"))
    assert "paint-order" not in st and st.get("text-anchor") == "end"
    b = engine.bboxes(doc)
    for sid, bar_y in (("bar_x1", 52), ("bar_concorde", 64)):
        lab = b[f"{sid}-label-2"]
        assert lab[1] + lab[3] / 2 == pytest.approx(bar_y, abs=0.4)  # dy = 0 → vertically centred on the point
    assert b["bar_concorde-label-2"][0] + b["bar_concorde-label-2"][2] == pytest.approx(50 + 2179 * 0.056 - 2, abs=0.3)
    with pytest.raises(DocumentError, match="label_anchor"):
        engine.plot(doc, "speed", [{"points": [[0, 1]], "point_labels": ["x"], "label_anchor": "left"}])
