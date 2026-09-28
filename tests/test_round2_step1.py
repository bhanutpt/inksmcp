"""Round-2 build step 1 (D-024, D-026): files in — images, SVG import, specs and rows from files (E25)."""
import json
import struct

import pytest
from mcp import Client

from inksmcp import files, server
from inksmcp.document import SRC_ATTR, XLINK_NS, Document, DocumentError

HREF = f"{{{XLINK_NS}}}href"


@pytest.fixture
def fresh_session(engine, monkeypatch):
    s = server.Session()
    s._engine = engine
    monkeypatch.setattr(server, "session", s)
    return s


def text(r):
    assert not r.is_error, r.content
    return json.loads(r.content[0].text)


@pytest.fixture(scope="module")
def pic(engine, tmp_path_factory):
    """A 200 x 100 px PNG: red left half, blue right half."""
    src = Document.create(200, 100, "px")
    src.add({"type": "rect", "x": 0, "y": 0, "width": 100, "height": 100, "fill": "#d00"})
    src.add({"type": "rect", "x": 100, "y": 0, "width": 100, "height": 100, "fill": "#00d"})
    return engine.export(src, tmp_path_factory.mktemp("pics") / "pic.png", "png")


# -- image sizes from headers -------------------------------------------------------------------
def test_image_size_from_headers(pic, tmp_path):
    assert files.image_size(pic) == (200, 100)
    jpg = tmp_path / "a.jpg"  # SOI, an APP0 segment, then SOF0 with height 480, width 640
    jpg.write_bytes(b"\xff\xd8" + b"\xff\xe0" + struct.pack(">H", 6) + b"JFIF" +
                    b"\xff\xc0" + struct.pack(">HBHH", 11, 8, 480, 640) + b"\x03" * 6)
    assert files.image_size(jpg) == (640, 480)
    gif = tmp_path / "a.gif"
    gif.write_bytes(b"GIF89a" + struct.pack("<HH", 32, 16) + b"\0" * 8)
    assert files.image_size(gif) == (32, 16)


# -- the image element ------------------------------------------------------------------------------
def test_image_element_sizes_links_and_fits(engine, pic):
    doc = Document.create(210, 150, "mm")
    doc.add({"type": "image", "id": "nat", "href": str(pic)})  # a plain path: stored as a file URI (E25)
    el = doc.get("nat")
    assert el.get(HREF).startswith("file:///") and el.get(SRC_ATTR) == str(pic)
    assert (float(el.get("width")), float(el.get("height"))) == pytest.approx((52.9167, 26.4583), abs=1e-3)  # 96 dpi
    doc.add({"type": "image", "id": "w", "href": str(pic), "x": 60, "y": 0, "width": 40})  # ratio kept
    assert doc.get("w").get("height") == "20"
    doc.add({"type": "image", "id": "cover", "href": str(pic), "x": 110, "y": 0, "width": 30, "height": 30,
             "object_fit": "cover", "embed": True})
    assert doc.get("cover").get("preserveAspectRatio") == "xMidYMid slice"
    assert doc.get("cover").get(HREF).startswith("data:image/png;base64,")
    b = engine.bboxes(doc)
    assert b["w"] == pytest.approx((60, 0, 40, 20), abs=0.01) and b["cover"] == pytest.approx((110, 0, 30, 30), abs=0.01)
    with pytest.raises(DocumentError, match="not found"):
        doc.add({"type": "image", "href": str(pic.parent / "missing.png")})
    with pytest.raises(DocumentError, match="local files"):
        doc.add({"type": "image", "href": "https://example.com/a.png"})


# -- SVG import -----------------------------------------------------------------------------------------
def test_import_svg_scales_renames_and_keeps_references(engine, tmp_path):
    part = Document.create(100, 50, "px")  # 100 px = 26.458 mm
    part.add({"type": "rect", "id": "a", "x": 0, "y": 0, "width": 100, "height": 50, "fill": "#0a0", "layer": "Base"})
    part.add({"type": "rect", "id": "win", "x": 10, "y": 10, "width": 30, "height": 30, "layer": "Base"})
    part.add({"type": "circle", "id": "c", "cx": 70, "cy": 25, "r": 30, "clip": "win", "layer": "Base"})
    part.save(tmp_path / "part.svg")
    doc = Document.create(210, 100, "mm")
    doc.add({"type": "rect", "id": "a", "x": 0, "y": 0, "width": 5, "height": 5})  # clashes with the file's "a"
    doc.add({"type": "rect", "id": "c-clip", "x": 0, "y": 0, "width": 5, "height": 5})  # clashes with its clipPath
    r = files.import_svg(doc, tmp_path / "part.svg", (20, 30), None, None, doc.root, "part")
    assert r["renamed"] == {"a": "part-a", "c-clip": "part-c-clip"} and r["layers_as_groups"] == ["Base"]
    assert r["size"] == pytest.approx([26.458, 13.229], abs=1e-3)
    assert doc.get("c").get("clip-path") == "url(#part-c-clip)"  # the reference follows the rename
    b = engine.bboxes(doc)
    assert b["part"] == pytest.approx((20, 30, 26.458, 13.229), abs=0.01)
    r = files.import_svg(doc, tmp_path / "part.svg", (0, 60), 100, None, doc.root, "part2")  # width scales it
    assert engine.bboxes(doc)["part2"] == pytest.approx((0, 60, 100, 50), abs=0.01)


# -- through the tools: import_file, elements_path, rows_path ------------------------------------------------
@pytest.mark.anyio
async def test_files_in_through_the_tools(fresh_session, engine, pic, tmp_path):
    (tmp_path / "specs.json").write_text(json.dumps({"defaults": {"fill": "#123456"}, "elements": [
        {"type": "rect", "id": f"r-{k}", "x": 10 * k, "y": 5, "width": 8, "height": 8} for k in range(1, 21)]}))
    (tmp_path / "rows.csv").write_text("sym,num,x\nH,1,10\nHe,2,30\nLi,3,50\n", encoding="utf-8")
    async with Client(server.mcp) as c:
        await c.call_tool("document_create", {"width": 250, "height": 100, "unit": "mm"})
        await c.call_tool("document_save", {"path": str(tmp_path / "work.svg")})  # relative paths start here
        r = text(await c.call_tool("add_elements", {"elements_path": "specs.json"}))
        assert r["ids"] == ["r-1..r-20"] and r["source"]["elements"] == 20
        r = text(await c.call_tool("repeat", {"rows_path": "rows.csv", "step": [0, 0], "template": [
            {"type": "text", "id": "sym", "x": "{x}", "y": 40, "text": "{sym}{num}"}]}))
        assert r["ids"]["sym"] == ["sym-1..sym-3"]
        r = text(await c.call_tool("import_file", {"path": str(pic), "at": [100, 50], "width": 60,
                                                   "object_fit": "cover", "layer": "Photos"}))
        assert r["bbox"] == pytest.approx([100, 50, 60, 30], abs=0.01)
        r = await c.call_tool("add_elements", {"elements_path": "nope.json"})
        assert r.is_error and "not found" in r.content[0].text
    doc = fresh_session.docs["doc1"]
    assert "fill:#123456" in doc.get("r-7").get("style")
    assert doc.text_of(doc.get("sym-2")) == "He2"
