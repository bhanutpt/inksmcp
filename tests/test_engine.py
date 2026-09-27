"""Inkscape-backed operations. Each test encodes a finding from docs/05-inkscape-notes.md."""
import pytest

from inksmcp.document import Document, parse_style
from inksmcp.inkscape import InkscapeError

from .conftest import png_size


@pytest.fixture
def mm_doc():
    doc = Document.create(100, 50, "mm")
    doc.add({"type": "rect", "id": "a", "x": 10, "y": 10, "width": 20, "height": 20, "fill": "#3366ff"})
    doc.add({"type": "circle", "id": "b", "cx": 30, "cy": 20, "r": 10, "fill": "#ff6633"})
    doc.add({"type": "text", "id": "t", "x": 60, "y": 30, "text": "Hello", "font_size": 8})
    return doc


def test_bboxes_are_in_user_units_not_px(engine, mm_doc):
    # E04: query-all reports px at 96 dpi; we convert back to mm user units.
    boxes = engine.bboxes(mm_doc)
    assert boxes["a"] == pytest.approx((10, 10, 20, 20), abs=0.01)
    assert boxes["b"] == pytest.approx((20, 10, 20, 20), abs=0.01)
    x, y, w, h = boxes["t"]
    assert 59 < x < 62 and 20 < y < 31 and w > 10 and h > 3  # text has a real measured box


def test_union_keeps_style(engine, mm_doc):
    # E01/E03: union drops presentation attrs, keeps style="" — we always write style.
    engine.run_actions(mm_doc, ["path-union"], select=["a", "b"])
    ids = mm_doc.ids()
    assert "a" in ids and "b" not in ids
    assert parse_style(mm_doc.get("a").get("style"))["fill"] == "#3366ff"
    assert mm_doc.get("a").tag.endswith("path")


def test_actions_on_missing_id_raise(engine, mm_doc):
    from inksmcp.document import DocumentError
    with pytest.raises(DocumentError, match="nope"):
        engine.run_actions(mm_doc, ["path-union"], select=["nope"])


def test_blocked_actions(engine, mm_doc):
    for bad in ["quit", "file-save", "export-do", "path-union;quit"]:
        with pytest.raises(InkscapeError):
            engine.run_actions(mm_doc, [bad])


def test_layers_survive_actions(engine):
    doc = Document.create(100, 100)
    doc.add({"type": "text", "id": "t", "x": 10, "y": 50, "text": "Hi", "layer": "Text"})
    engine.run_actions(doc, ["object-to-path"], select=["t"])
    [layer] = doc.layers()
    assert layer[0].get("id") == "t"


def test_export_settings_do_not_leak_between_exports(engine, mm_doc, tmp_path):
    # E05/E06: export-id / export-width / area are sticky for the whole shell session.
    def size(**kw):
        return png_size(engine.export(mm_doc, tmp_path / "x.png", **kw).read_bytes())

    page = (378, 189)  # 100x50 mm at 96 dpi
    assert size() == page
    assert size(ids=["a"], width=200) == (200, 200)
    assert size() == page
    dw, dh = size(area="drawing")  # content spans ~10..85 mm x 10..31 mm
    assert 200 < dw < 378 and 60 < dh < 189
    assert size(ids=["b"]) == (76, 76)  # 20 mm circle
    assert size(dpi=192) == (756, 378)
    assert size() == page


def test_export_formats(engine, mm_doc, tmp_path):
    assert engine.export(mm_doc, tmp_path / "x.pdf").read_bytes()[:4] == b"%PDF"
    plain = engine.export(mm_doc, tmp_path / "x.svg", "plain-svg").read_text(encoding="utf-8")
    assert "sodipodi" not in plain and "<rect" in plain


def test_export_to_path_with_semicolon(engine, mm_doc, tmp_path):
    out = engine.export(mm_doc, tmp_path / "we;ird.png")
    assert out.exists()


def test_render_png_longest_side(engine, mm_doc):
    assert png_size(engine.render_png(mm_doc, max_size=400)) == (400, 200)
    w, h = png_size(engine.render_png(mm_doc, max_size=300, ids=["a"]))
    assert max(w, h) == 300
