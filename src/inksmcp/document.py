"""Domain layer: an SVG document the agent edits through intent-level element specs.

All coordinates are in document *user units* (the unit the document was created with).
Styles are always written to the `style` attribute: Inkscape drops presentation
attributes like fill="..." on boolean ops (experiment E03).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from lxml import etree

SVG_NS = "http://www.w3.org/2000/svg"
INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"
SODIPODI_NS = "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
XLINK_NS = "http://www.w3.org/1999/xlink"
NSMAP = {None: SVG_NS, "inkscape": INKSCAPE_NS, "sodipodi": SODIPODI_NS, "xlink": XLINK_NS}

PX_PER_UNIT = {"px": 1.0, "mm": 96 / 25.4, "cm": 96 / 2.54, "in": 96.0, "pt": 96 / 72, "pc": 16.0}

# Friendly style keys -> CSS properties.
STYLE_KEYS = {
    "fill": "fill",
    "stroke": "stroke",
    "stroke_width": "stroke-width",
    "opacity": "opacity",
    "fill_opacity": "fill-opacity",
    "stroke_opacity": "stroke-opacity",
    "stroke_dasharray": "stroke-dasharray",
    "stroke_linecap": "stroke-linecap",
    "stroke_linejoin": "stroke-linejoin",
    "font_size": "font-size",
    "font_family": "font-family",
    "font_weight": "font-weight",
    "font_style": "font-style",
    "text_anchor": "text-anchor",
}
PRESENTATION_ATTRS = set(STYLE_KEYS.values())

GEOMETRY = {
    "rect": ("x", "y", "width", "height", "rx", "ry"),
    "circle": ("cx", "cy", "r"),
    "ellipse": ("cx", "cy", "rx", "ry"),
    "line": ("x1", "y1", "x2", "y2"),
    "polyline": ("points",),
    "polygon": ("points",),
    "path": ("d",),
    "text": ("x", "y", "text", "line_height"),
    "group": (),
}
COMMON = {"type", "id", "label", "layer", "parent", "transform", "style"}

SHAPE_TAGS = {"rect", "circle", "ellipse", "line", "polyline", "polygon", "path", "text", "g", "image", "use"}


class DocumentError(ValueError):
    """Invalid request against a document (bad id, bad spec...)."""


def _q(tag: str, ns: str = SVG_NS) -> str:
    return f"{{{ns}}}{tag}"


def _local(el: etree._Element) -> str:
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


def _num(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:.4f}".rstrip("0").rstrip(".")
    return str(v)


def parse_length(value: str | None) -> tuple[float, str] | None:
    if not value:
        return None
    m = re.fullmatch(r"\s*([-+]?[\d.]+(?:e[-+]?\d+)?)\s*([a-z%]*)\s*", value, re.I)
    if not m:
        return None
    return float(m.group(1)), (m.group(2) or "px").lower()


def parse_style(style: str | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in (style or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def format_style(style: dict[str, str]) -> str:
    return ";".join(f"{k}:{v}" for k, v in style.items() if v is not None and v != "")


class Document:
    def __init__(self, root: etree._Element, path: Path | None = None):
        self.root = root
        self.path = path
        self._counter = 0
        self.ensure_ids()

    # -- construction ----------------------------------------------------
    @classmethod
    def create(cls, width: float, height: float, unit: str = "px", background: str | None = None) -> "Document":
        if unit not in PX_PER_UNIT:
            raise DocumentError(f"Unknown unit {unit!r}; use one of {sorted(PX_PER_UNIT)}")
        root = etree.Element(_q("svg"), nsmap=NSMAP)
        root.set("width", f"{_num(width)}{unit}")
        root.set("height", f"{_num(height)}{unit}")
        root.set("viewBox", f"0 0 {_num(width)} {_num(height)}")
        root.set("version", "1.1")
        root.set("id", "svg1")
        nv = etree.SubElement(root, _q("namedview", SODIPODI_NS))
        nv.set("id", "namedview1")
        nv.set(_q("document-units", INKSCAPE_NS), unit)
        if background:
            nv.set("pagecolor", background)
        etree.SubElement(root, _q("defs")).set("id", "defs1")
        doc = cls(root)
        if background:
            doc.add({"type": "rect", "id": "background", "x": 0, "y": 0, "width": width, "height": height,
                     "fill": background, "stroke": "none"})
        return doc

    @classmethod
    def open(cls, path: str | Path) -> "Document":
        path = Path(path)
        if not path.exists():
            raise DocumentError(f"File not found: {path}")
        return cls.from_bytes(path.read_bytes(), path)

    @classmethod
    def from_bytes(cls, data: bytes, path: Path | None = None) -> "Document":
        parser = etree.XMLParser(remove_blank_text=False, huge_tree=True, resolve_entities=False)
        root = etree.fromstring(data, parser)
        if _local(root) != "svg":
            raise DocumentError("Not an SVG document.")
        return cls(root, path)

    def to_bytes(self) -> bytes:
        return etree.tostring(self.root, xml_declaration=True, encoding="UTF-8", standalone=False)

    def save(self, path: str | Path | None = None) -> Path:
        target = Path(path) if path else self.path
        if not target:
            raise DocumentError("No path given and document has never been saved.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.to_bytes())
        self.path = target
        return target

    # -- geometry of the page -------------------------------------------
    @property
    def viewbox(self) -> tuple[float, float, float, float]:
        vb = self.root.get("viewBox")
        if vb:
            x, y, w, h = (float(v) for v in re.split(r"[\s,]+", vb.strip()))
            return x, y, w, h
        w = parse_length(self.root.get("width")) or (100.0, "px")
        h = parse_length(self.root.get("height")) or (100.0, "px")
        return 0.0, 0.0, w[0] * PX_PER_UNIT.get(w[1], 1), h[0] * PX_PER_UNIT.get(h[1], 1)

    @property
    def px_per_user_unit(self) -> float:
        """Inkscape's --query-* results are in px (96 dpi); divide by this to get user units."""
        w = parse_length(self.root.get("width"))
        vb_w = self.viewbox[2]
        if not w or w[1] == "%" or not vb_w:
            return 1.0
        return w[0] * PX_PER_UNIT.get(w[1], 1.0) / vb_w

    @property
    def unit(self) -> str:
        w = parse_length(self.root.get("width"))
        return w[1] if w and w[1] in PX_PER_UNIT else "px"

    # -- ids -------------------------------------------------------------
    def _new_id(self, prefix: str) -> str:
        while True:
            self._counter += 1
            cand = f"{prefix}{self._counter}"
            if not self._find(cand):
                return cand

    def _find(self, id_: str) -> etree._Element | None:
        found = self.root.xpath("//*[@id=$i]", i=id_)
        return found[0] if found else None

    def get(self, id_: str) -> etree._Element:
        el = self._find(id_)
        if el is None:
            raise DocumentError(f"No element with id {id_!r}. Use inspect to list ids.")
        return el

    def ensure_ids(self) -> None:
        for el in self.root.iter():
            if isinstance(el.tag, str) and el.get("id") is None and _local(el) in SHAPE_TAGS | {"tspan"}:
                el.set("id", self._new_id(_local(el)))

    # -- layers ----------------------------------------------------------
    def layers(self) -> list[etree._Element]:
        return [el for el in self.root if _local(el) == "g" and el.get(_q("groupmode", INKSCAPE_NS)) == "layer"]

    def layer(self, name: str, create: bool = True) -> etree._Element:
        for lay in self.layers():
            if lay.get(_q("label", INKSCAPE_NS)) == name or lay.get("id") == name:
                return lay
        if not create:
            raise DocumentError(f"No layer named {name!r}.")
        lay = etree.SubElement(self.root, _q("g"))
        lay.set("id", self._new_id("layer"))
        lay.set(_q("groupmode", INKSCAPE_NS), "layer")
        lay.set(_q("label", INKSCAPE_NS), name)
        return lay

    # -- element specs ---------------------------------------------------
    def add(self, spec: dict[str, Any]) -> str:
        spec = dict(spec)
        kind = spec.get("type")
        if kind not in GEOMETRY:
            raise DocumentError(f"Unknown element type {kind!r}; use one of {sorted(GEOMETRY)}")
        self._check_keys(kind, spec)
        if spec.get("parent"):
            parent = self.get(spec["parent"])
        elif spec.get("layer"):
            parent = self.layer(spec["layer"])
        else:
            parent = self.root
        tag = "g" if kind == "group" else kind
        el = etree.SubElement(parent, _q(tag))
        new_id = spec.get("id") or self._new_id(tag)
        if self._find(new_id) is not None and self._find(new_id) is not el:
            parent.remove(el)
            raise DocumentError(f"Id {new_id!r} already exists.")
        el.set("id", new_id)
        if kind == "text":
            # sensible defaults so text is visible without the agent thinking about it
            spec.setdefault("font_size", 16 if self.unit == "px" else 5)
            spec.setdefault("fill", "#000000")
        self._apply(el, kind, spec)
        return new_id

    def update(self, id_: str, props: dict[str, Any]) -> None:
        el = self.get(id_)
        kind = "group" if _local(el) == "g" else _local(el)
        if kind not in GEOMETRY:
            raise DocumentError(f"Cannot update element of type {_local(el)!r} yet.")
        props = {k: v for k, v in props.items() if k != "type"}
        self._check_keys(kind, props)
        if "id" in props and props["id"] != id_:
            if self._find(props["id"]) is not None:
                raise DocumentError(f"Id {props['id']!r} already exists.")
        self._apply(el, kind, props)

    def delete(self, id_: str) -> None:
        el = self.get(id_)
        el.getparent().remove(el)

    def _check_keys(self, kind: str, spec: dict[str, Any]) -> None:
        allowed = COMMON | set(GEOMETRY[kind]) | set(STYLE_KEYS)
        unknown = set(spec) - allowed
        if unknown:
            raise DocumentError(
                f"Unknown keys for {kind}: {sorted(unknown)}. Allowed: {sorted(allowed - {'type'})}"
            )

    def _apply(self, el: etree._Element, kind: str, spec: dict[str, Any]) -> None:
        if "id" in spec and spec["id"]:
            el.set("id", spec["id"])
        if "label" in spec:
            el.set(_q("label", INKSCAPE_NS), spec["label"])
        if "transform" in spec:
            if spec["transform"]:
                el.set("transform", spec["transform"])
            else:
                el.attrib.pop("transform", None)
        for key in GEOMETRY[kind]:
            if key not in spec or key in ("text", "line_height"):
                continue
            val = spec[key]
            if key == "points" and not isinstance(val, str):
                val = " ".join(f"{_num(p[0])},{_num(p[1])}" for p in val)
            el.set(key, _num(val))
        # style: raw style first, friendly keys override; presentation attrs are folded in
        style = parse_style(el.get("style"))
        for attr in list(el.attrib):
            if attr in PRESENTATION_ATTRS:
                style.setdefault(attr, el.attrib.pop(attr))
        raw = spec.get("style")
        if isinstance(raw, str):
            style.update(parse_style(raw))
        elif isinstance(raw, dict):
            style.update({k.replace("_", "-"): str(v) for k, v in raw.items()})
        for key, css in STYLE_KEYS.items():
            if key in spec and spec[key] is not None:
                val = spec[key]
                if css == "font-size" and isinstance(val, (int, float)):
                    val = f"{_num(val)}px"
                style[css] = _num(val)
        if kind in ("line", "polyline") and "stroke" not in style:
            style["stroke"] = "#000000"  # otherwise invisible
        if kind in ("line", "polyline") and "fill" not in style:
            style["fill"] = "none"
        if style:
            el.set("style", format_style(style))
        if kind == "text" and "text" in spec:
            self._set_text(el, str(spec["text"]), spec.get("line_height", 1.25))

    def _set_text(self, el: etree._Element, text: str, line_height: float) -> None:
        for child in list(el):
            el.remove(child)
        el.text = None
        lines = text.split("\n")
        if len(lines) == 1:
            el.text = text
            return
        x = el.get("x", "0")
        for i, line in enumerate(lines):
            t = etree.SubElement(el, _q("tspan"))
            t.set("id", self._new_id("tspan"))
            t.set(_q("role", SODIPODI_NS), "line")
            t.set("x", x)
            if i:
                t.set("dy", f"{line_height}em")
            t.text = line

    # -- inspection ------------------------------------------------------
    def outline(self, bboxes: dict[str, tuple[float, float, float, float]] | None = None,
                max_depth: int = 6) -> list[dict[str, Any]]:
        """Compact, agent-friendly tree of drawable elements."""

        def node(el: etree._Element, depth: int) -> dict[str, Any] | None:
            tag = _local(el)
            if tag not in SHAPE_TAGS:
                return None
            is_layer = tag == "g" and el.get(_q("groupmode", INKSCAPE_NS)) == "layer"
            d: dict[str, Any] = {"id": el.get("id"), "type": "layer" if is_layer else ("group" if tag == "g" else tag)}
            label = el.get(_q("label", INKSCAPE_NS))
            if label:
                d["label"] = label
            if bboxes and el.get("id") in bboxes:
                d["bbox"] = [round(v, 2) for v in bboxes[el.get("id")]]
            style = parse_style(el.get("style"))
            for k in ("fill", "stroke", "opacity"):
                if k in style and tag != "g":
                    d[k] = style[k]
            if tag == "text":
                spans = [c for c in el if _local(c) == "tspan"]
                d["text"] = "\n".join("".join(s.itertext()) for s in spans) if spans else "".join(el.itertext())
            if el.get("transform"):
                d["transform"] = el.get("transform")
            if tag == "g" and depth < max_depth:
                kids = [n for n in (node(c, depth + 1) for c in el) if n]
                d["children"] = kids
            elif tag == "g":
                d["children_truncated"] = len(el)
            return d

        return [n for n in (node(c, 0) for c in self.root) if n]

    def ids(self) -> list[str]:
        return [el.get("id") for el in self.root.iter() if isinstance(el.tag, str) and el.get("id")]
