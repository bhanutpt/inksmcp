"""Domain layer: pure lxml, no Inkscape needed."""
import pytest

from inksmcp.document import Document, DocumentError, parse_style


def test_create_sets_units_and_viewbox():
    doc = Document.create(210, 297, "mm")
    assert doc.root.get("width") == "210mm"
    assert doc.viewbox == (0, 0, 210, 297)
    assert doc.unit == "mm"
    assert doc.px_per_user_unit == pytest.approx(96 / 25.4)


def test_add_writes_style_attribute_not_presentation_attrs():
    doc = Document.create(100, 100)
    rid = doc.add({"type": "rect", "x": 1, "y": 2, "width": 3, "height": 4, "fill": "red", "stroke_width": 2})
    el = doc.get(rid)
    assert el.get("fill") is None
    assert parse_style(el.get("style")) == {"fill": "red", "stroke-width": "2"}


def test_presentation_attrs_are_folded_into_style_on_update():
    doc = Document.from_bytes(b'<svg xmlns="http://www.w3.org/2000/svg"><rect id="r" fill="blue" width="1" height="1"/></svg>')
    doc.update("r", {"stroke": "black"})
    el = doc.get("r")
    assert el.get("fill") is None
    assert parse_style(el.get("style")) == {"fill": "blue", "stroke": "black"}


def test_ids_are_unique_and_generated():
    doc = Document.create(100, 100)
    a = doc.add({"type": "circle", "cx": 1, "cy": 1, "r": 1})
    b = doc.add({"type": "circle", "cx": 1, "cy": 1, "r": 1})
    assert a != b
    with pytest.raises(DocumentError, match="already exists"):
        doc.add({"type": "rect", "id": a})


def test_unknown_keys_are_rejected_with_help():
    doc = Document.create(100, 100)
    with pytest.raises(DocumentError, match="Allowed"):
        doc.add({"type": "rect", "colour": "red"})


def test_layers_and_multiline_text():
    doc = Document.create(100, 100)
    tid = doc.add({"type": "text", "x": 10, "y": 20, "text": "one\ntwo", "layer": "Labels"})
    [layer] = doc.layers()
    assert layer.get("{http://www.inkscape.org/namespaces/inkscape}label") == "Labels"
    outline = doc.outline()
    assert outline[0]["type"] == "layer"
    assert outline[0]["children"][0] == {"id": tid, "type": "text", "fill": "#000000", "text": "one\ntwo"}


def test_lines_get_visible_default_stroke():
    doc = Document.create(100, 100)
    lid = doc.add({"type": "line", "x1": 0, "y1": 0, "x2": 10, "y2": 10})
    assert parse_style(doc.get(lid).get("style")) == {"stroke": "#000000", "fill": "none"}


def test_tidy_numbers_only_touches_given_elements():
    doc = Document.from_bytes(
        b'<svg xmlns="http://www.w3.org/2000/svg"><g id="g" transform="translate(-34.999973,1e-06)">'
        b'<rect id="r" x="81.405006" y="-0.0000001" width="10" height="10"/></g>'
        b'<rect id="other" x="1.23456789" width="1" height="1"/></svg>')
    doc.tidy_numbers(["g"])
    assert doc.get("g").get("transform") == "translate(-35,0)"
    assert (doc.get("r").get("x"), doc.get("r").get("y")) == ("81.405", "0")
    assert doc.get("other").get("x") == "1.23456789"


def test_save_and_reopen_roundtrip(tmp_path):
    doc = Document.create(50, 50, background="#eeeeee")
    doc.add({"type": "polygon", "points": [[0, 0], [10, 0], [5, 8]], "fill": "green"})
    path = doc.save(tmp_path / "a.svg")
    again = Document.open(path)
    assert [n["id"] for n in again.outline()] == [n["id"] for n in doc.outline()]
