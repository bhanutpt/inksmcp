"""Files in (D-024 step 1): image sizes from headers, JSON/CSV data for specs and rows, SVG import.

Data-heavy work (report 8: 51 kB of map geometry; report 7: 20k chars of specs pasted twice) must not
pass through the model, so tools read these files themselves.
"""
from __future__ import annotations

import copy
import csv
import json
import re
import struct
from pathlib import Path
from typing import Any

from lxml import etree

from .document import (CLIP_ATTR, FIT_ATTR, INKSCAPE_NS, LABEL_FOR, ROUTE_ATTR, SHAPE_TAGS,
                       Document, DocumentError, _local, _q, parse_length)

IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
               ".webp": "image/webp", ".svg": "image/svg+xml", ".bmp": "image/bmp"}


def resolve(path: str, doc: Document | None = None) -> Path:
    """Absolute path; a relative one is taken from the document's folder (else the working directory)."""
    p = Path(path).expanduser()
    if not p.is_absolute() and doc is not None and doc.path:
        p = Path(doc.path).parent / p
    p = p.resolve()
    if not p.is_file():
        raise DocumentError(f"File not found: {p}")
    return p


def image_size(path: Path) -> tuple[int, int] | None:
    """Pixel size from the PNG / GIF / JPEG header, or None (then width and height must be given)."""
    with open(path, "rb") as f:
        head = f.read(32)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", head[16:24])
        if head[:6] in (b"GIF87a", b"GIF89a"):
            return struct.unpack("<HH", head[6:10])
        if head[:2] == b"\xff\xd8":  # JPEG: walk the segments to the first SOFn
            f.seek(2)
            while True:
                marker = f.read(2)
                if len(marker) < 2 or marker[0] != 0xFF:
                    return None
                if marker[1] in (0xD8, 0x01) or 0xD0 <= marker[1] <= 0xD7:
                    continue
                size = struct.unpack(">H", f.read(2))[0]
                if 0xC0 <= marker[1] <= 0xCF and marker[1] not in (0xC4, 0xC8, 0xCC):
                    h, w = struct.unpack(">xHH", f.read(5))
                    return w, h
                f.seek(size - 2, 1)
    return None


def _number(v: str) -> Any:
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


def read_rows(path: Path) -> list[dict[str, Any]]:
    """Rows from .json (a list of objects, or {"rows": [...]}) or .csv (header line; numbers parsed)."""
    if path.suffix.lower() == ".csv":
        with open(path, newline="", encoding="utf-8-sig") as f:
            return [{k: _number(v) for k, v in row.items()} for row in csv.DictReader(f)]
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = data.get("rows") if isinstance(data, dict) else data
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        raise DocumentError(f"{path.name}: expected a JSON list of row objects (or {{\"rows\": [...]}}).")
    return rows


def read_specs(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Element specs from .json: a list, or {"elements": [...], "defaults": {...}}."""
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    elements, defaults = (data.get("elements"), data.get("defaults") or {}) if isinstance(data, dict) else (data, {})
    if not isinstance(elements, list) or not all(isinstance(e, dict) for e in elements):
        raise DocumentError(f"{path.name}: expected a JSON list of element specs (or {{\"elements\": [...]}}).")
    return elements, defaults


# -- SVG import ---------------------------------------------------------------------------------
_SKIP = {"defs", "metadata", "namedview", "title", "desc"}
_REF = re.compile(r"url\(#([^)]+)\)")


def _size_px(root: etree._Element) -> tuple[float, float, float, float, float, float]:
    """(vb_x, vb_y, vb_w, vb_h, px per user unit x, y) of an SVG root."""
    vb = [float(v) for v in re.split(r"[\s,]+", root.get("viewBox", "").strip()) if v] or None
    px = {"px": 1.0, "mm": 96 / 25.4, "cm": 96 / 2.54, "in": 96.0, "pt": 96 / 72, "pc": 16.0}
    dims = []
    for k in ("width", "height"):
        L = parse_length(root.get(k))
        dims.append(L[0] * px.get(L[1], 1.0) if L and L[1] != "%" else None)
    if vb is None or len(vb) != 4:
        if None in dims:
            raise DocumentError("The SVG has neither a viewBox nor absolute width/height.")
        vb = [0, 0, dims[0], dims[1]]
    w_px = dims[0] if dims[0] is not None else vb[2]
    h_px = dims[1] if dims[1] is not None else vb[3]
    return vb[0], vb[1], vb[2], vb[3], w_px / vb[2], h_px / vb[3]


def import_svg(doc: Document, path: Path, at: tuple[float, float], width: float | None, height: float | None,
               parent: etree._Element, gid: str) -> dict[str, Any]:
    """Copy an SVG file's drawing into one group: scaled to the document's units (or to width/height),
    its top-left at `at`. Its defs join ours; clashing ids are renamed and references follow; its
    layers become groups labelled with the layer name."""
    try:
        src = etree.parse(str(path), etree.XMLParser(remove_blank_text=False, huge_tree=True)).getroot()
    except etree.XMLSyntaxError as e:
        raise DocumentError(f"{path.name} is not valid SVG: {e}") from e
    if _local(src) != "svg":
        raise DocumentError(f"{path.name} is not an SVG document.")
    vbx, vby, vbw, vbh, sx_px, sy_px = _size_px(src)
    sx, sy = sx_px / doc.px_per_user_unit, sy_px / doc.px_per_user_unit  # file units -> ours
    if width and height:
        sx, sy = width / vbw, height / vbh
    elif width:
        sx = sy = width / vbw
    elif height:
        sx = sy = height / vbh
    # what gets copied: the defs' children and the drawable top-level elements
    def_nodes = [d for c in src if isinstance(c.tag, str) and _local(c) == "defs" for d in c]
    shapes = [c for c in src if isinstance(c.tag, str) and _local(c) not in _SKIP
              and _local(c) in SHAPE_TAGS | {"switch", "a", "foreignObject"}]
    # clashing ids get a prefix; collect the rename map over everything copied first
    taken = {e.get("id") for e in doc.root.iter() if isinstance(e.tag, str) and e.get("id")}
    renames: dict[str, str] = {}
    for el in (n for top in def_nodes + shapes for n in top.iter()):
        if isinstance(el.tag, str) and el.get("id") in taken:
            old, n = el.get("id"), 1
            new = f"{gid}-{old}"
            while new in taken or new in renames.values():
                n += 1
                new = f"{gid}-{old}-{n}"
            renames[old] = new
    if gid in taken:
        raise DocumentError(f"Id {gid!r} already exists.")
    g = etree.SubElement(parent, _q("g"))
    g.set("id", gid)
    g.set(_q("label", INKSCAPE_NS), path.name)
    t = f"translate({at[0]:g},{at[1]:g}) scale({sx:.6g},{sy:.6g})" if sx != sy else \
        f"translate({at[0]:g},{at[1]:g}) scale({sx:.6g})"
    if vbx or vby:
        t += f" translate({-vbx:g},{-vby:g})"
    g.set("transform", t)
    new_defs = [copy.deepcopy(d) for d in def_nodes]
    if new_defs:
        doc._defs().extend(new_defs)
    for child in shapes:
        g.append(copy.deepcopy(child))
    targets = [g] + new_defs
    layers = []
    for top in targets:
        for el in top.iter():
            if not isinstance(el.tag, str):
                continue
            if el is not g and el.get(_q("groupmode", INKSCAPE_NS)) == "layer":
                del el.attrib[_q("groupmode", INKSCAPE_NS)]  # a layer inside a group is just a group
                layers.append(el.get(_q("label", INKSCAPE_NS)) or el.get("id"))
            _rename_refs(el, renames)
    doc.ensure_ids()
    return {"id": gid, "elements": len(shapes), "scale": [round(sx, 6), round(sy, 6)],
            "size": [round(vbw * sx, 3), round(vbh * sy, 3)], "layers_as_groups": layers,
            **({"renamed": renames} if renames else {})}


def _rename_refs(el: etree._Element, renames: dict[str, str]) -> None:
    if not renames:
        return
    for attr, val in list(el.attrib.items()):
        if attr == "id":
            if val in renames:
                el.set("id", renames[val])
        elif attr in (FIT_ATTR, ROUTE_ATTR):
            data = json.loads(val)
            for k in ("ids",) if attr == FIT_ATTR else ("from", "to"):
                if k in data:
                    data[k] = [renames.get(i, i) for i in data[k]] if isinstance(data[k], list) else renames.get(data[k], data[k])
            el.set(attr, json.dumps(data, separators=(",", ":")))
        elif attr in (LABEL_FOR, CLIP_ATTR) and val in renames:
            el.set(attr, renames[val])
        elif val.startswith("#") and val[1:] in renames:  # (xlink:)href, inkscape:connection-start/end
            el.set(attr, "#" + renames[val[1:]])
        elif "url(#" in val:  # clip-path, marker, fill in style="..."
            el.set(attr, _REF.sub(lambda m: f"url(#{renames.get(m.group(1), m.group(1))})", val))
