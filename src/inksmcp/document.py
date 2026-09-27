"""Domain layer: an SVG document the agent edits through intent-level element specs.

All coordinates are in document *user units* (the unit the document was created with).
Styles are always written to the `style` attribute: Inkscape drops presentation
attributes like fill="..." on boolean ops (experiment E03).
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from lxml import etree

SVG_NS = "http://www.w3.org/2000/svg"
INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"
SODIPODI_NS = "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
XLINK_NS = "http://www.w3.org/1999/xlink"
INKSMCP_NS = "urn:inksmcp"  # our own metadata; survives Inkscape round-trips (E09)
NSMAP = {None: SVG_NS, "inkscape": INKSCAPE_NS, "sodipodi": SODIPODI_NS, "xlink": XLINK_NS, "inksmcp": INKSMCP_NS}
etree.register_namespace("inksmcp", INKSMCP_NS)

CONN_START = f"{{{INKSCAPE_NS}}}connection-start"
CONN_END = f"{{{INKSCAPE_NS}}}connection-end"
LABEL_FOR = f"{{{INKSMCP_NS}}}label-for"
ARROW_ATTR = f"{{{INKSMCP_NS}}}arrow"  # block arrow parameters, so updates can regenerate the path
WRAP_ATTR = f"{{{INKSMCP_NS}}}wrap-width"  # text wraps to this width (user units)
PARA_ATTR = f"{{{INKSMCP_NS}}}paragraphs"  # the unwrapped text, so re-wrapping never loses breaks
CAP_HEIGHT_EM = 0.357  # half the default sans cap height (S4) — centres a label on a point without measuring
ROUTE_ATTR = f"{{{INKSMCP_NS}}}route"  # JSON route spec of connectors we route ourselves (sides/via)
GRID_ATTR = f"{{{INKSMCP_NS}}}grid"  # JSON axes of a grid, so `plot` can map data values
LABEL_POS = f"{{{INKSMCP_NS}}}label-position"
LABEL_OFFSET = f"{{{INKSMCP_NS}}}label-offset"
LABEL_SIDE = f"{{{INKSMCP_NS}}}label-side"
CONNECTOR_KEYS = {"from", "to", "id", "routing", "arrow", "stroke", "stroke_width", "stroke_dasharray",
                  "opacity", "layer", "label", "font_size", "label_color", "from_side", "to_side", "via",
                  "label_position", "label_offset", "label_side", "label_halo", "font_family", "font_weight"}

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
    "line": ("x1", "y1", "x2", "y2", "marker_start", "marker_end"),
    "polyline": ("points", "marker_start", "marker_end"),
    "polygon": ("points",),
    "path": ("d", "marker_start", "marker_end"),
    "text": ("x", "y", "text", "line_height", "vertical_anchor", "width"),
    "group": (),
    "arrow": ("x1", "y1", "x2", "y2", "shaft_width", "head_width", "head_length"),
}
# spec keys that are not written as same-named SVG attributes
NON_ATTR_KEYS = {"marker_start", "marker_end"}
TEXT_NON_ATTR_KEYS = {"text", "line_height", "vertical_anchor", "width"}
COMMON = {"type", "id", "label", "layer", "parent", "transform", "style"}
# where `y` sits on a text: baseline (SVG default), cap top, cap middle, or baseline of the last line
VERTICAL_ANCHORS = ("baseline", "top", "middle", "bottom")

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

    def page_backgrounds(self, tol: float = 1e-3) -> list[str]:
        """Top-level, untransformed rects that exactly cover the page (e.g. `background`).
        They are page decoration: page_fit ignores them and page resizing resizes them."""
        vx, vy, vw, vh = self.viewbox
        out = []
        for el in self.root:
            if _local(el) != "rect" or el.get("transform"):
                continue
            try:
                geom = [float(el.get(k, "0")) for k in ("x", "y", "width", "height")]
            except ValueError:
                continue
            if all(abs(a - b) <= tol for a, b in zip(geom, (vx, vy, vw, vh))):
                out.append(el.get("id"))
        return out

    def set_page_size(self, width: float, height: float) -> list[str]:
        """Resize the page to width x height user units with its origin at 0,0. The user-unit scale
        and the length unit are kept; page backgrounds are resized. Content is not moved."""
        if width <= 0 or height <= 0:
            raise DocumentError("Page width and height must be positive.")
        backgrounds = self.page_backgrounds()
        _, _, vb_w, vb_h = self.viewbox
        for attr, new, old_vb in (("width", width, vb_w), ("height", height, vb_h)):
            m = re.fullmatch(r"\s*([-+]?[\d.]+(?:e[-+]?\d+)?)\s*([a-z]*)\s*", self.root.get(attr, ""), re.I)
            if m and old_vb:  # keep the unit suffix and the length-per-user-unit ratio
                self.root.set(attr, f"{_num(round(new * float(m.group(1)) / old_vb, 4))}{m.group(2)}")
            else:  # missing or percentage: plain user units
                self.root.set(attr, _num(round(new, 4)))
        self.root.set("viewBox", f"0 0 {_num(round(width, 4))} {_num(round(height, 4))}")
        for bid in backgrounds:
            el = self.get(bid)
            for k, v in (("x", 0), ("y", 0), ("width", width), ("height", height)):
                el.set(k, _num(round(v, 4)))
        return backgrounds

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

    def free_id(self, base: str) -> str:
        """`base` if unused, else base-2, base-3, ..."""
        if self._find(base) is None:
            return base
        n = 2
        while self._find(f"{base}-{n}") is not None:
            n += 1
        return f"{base}-{n}"

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
        tag = {"group": "g", "arrow": "path"}.get(kind, kind)
        el = etree.SubElement(parent, _q(tag))
        new_id = spec.get("id") or self._new_id(kind if kind == "arrow" else tag)
        if self._find(new_id) is not None and self._find(new_id) is not el:
            parent.remove(el)
            raise DocumentError(f"Id {new_id!r} already exists.")
        el.set("id", new_id)
        if kind == "text":
            # sensible defaults so text is visible without the agent thinking about it
            spec.setdefault("font_size", 16 if self.unit == "px" else 5)
            spec.setdefault("fill", "#000000")
        try:
            self._apply(el, kind, spec)
        except DocumentError:
            parent.remove(el)
            raise
        return new_id

    def kind_of(self, el: etree._Element) -> str:
        if el.get(ARROW_ATTR):
            return "arrow"
        return "group" if _local(el) == "g" else _local(el)

    def update(self, id_: str, props: dict[str, Any]) -> None:
        el = self.get(id_)
        kind = self.kind_of(el)
        if kind not in GEOMETRY:
            raise DocumentError(f"Cannot update element of type {_local(el)!r} yet.")
        props = {k: v for k, v in props.items() if k != "type"}
        self._check_keys(kind, props)
        if "id" in props and props["id"] != id_:
            if self._find(props["id"]) is not None:
                raise DocumentError(f"Id {props['id']!r} already exists.")
        self._apply(el, kind, props)

    def delete(self, id_: str) -> list[str]:
        """Delete an element; connectors attached to it (or its children) and their labels go too.
        Returns every removed id."""
        el = self.get(id_)
        gone = {e.get("id") for e in el.iter() if isinstance(e.tag, str) and e.get("id")}
        el.getparent().remove(el)
        removed = [id_]
        for conn in self.connectors():
            if set(self.connector_ends(conn)) & gone:
                removed.append(conn.get("id"))
                conn.getparent().remove(conn)
                gone.add(conn.get("id"))
        for lab in self.root.xpath("//*[@inksmcp:label-for]", namespaces={"inksmcp": INKSMCP_NS}):
            if lab.get(LABEL_FOR) in gone:
                removed.append(lab.get("id"))
                lab.getparent().remove(lab)
        return removed

    # -- connectors ------------------------------------------------------
    def connectors(self, kind: str = "all") -> list[etree._Element]:
        """kind: 'native' (Inkscape routes them), 'routed' (we route them: sides/via), or 'all'."""
        out = []
        for e in self.root.iter():
            if not isinstance(e.tag, str):
                continue
            native = bool(e.get(CONN_START) or e.get(CONN_END))
            routed = e.get(ROUTE_ATTR) is not None
            if (kind == "all" and (native or routed)) or (kind == "native" and native) or (kind == "routed" and routed):
                out.append(e)
        return out

    @staticmethod
    def connector_ends(el: etree._Element) -> tuple[str, str]:
        if el.get(ROUTE_ATTR) is not None:
            r = json.loads(el.get(ROUTE_ATTR))
            return r["from"], r["to"]
        return el.get(CONN_START, "").lstrip("#"), el.get(CONN_END, "").lstrip("#")

    def default_stroke_width(self) -> float:
        return round(1.5 / self.px_per_user_unit, 4)

    def default_font_size(self) -> float:
        return 16 if self.unit == "px" else round(16 / self.px_per_user_unit, 2)

    def arrow_marker(self, color: str) -> str:
        """Id of an arrowhead marker filled with `color`, created in <defs> if needed.
        One marker per colour instead of fill:context-stroke, which not every SVG viewer supports."""
        mid = "inksmcp-arrow-" + (re.sub(r"[^A-Za-z0-9]", "", color) or "default")
        if self._find(mid) is None:
            defs = next((c for c in self.root if _local(c) == "defs"), None)
            if defs is None:
                defs = etree.Element(_q("defs"))
                defs.set("id", self._new_id("defs"))
                self.root.insert(0, defs)
            m = etree.SubElement(defs, _q("marker"))
            for k, v in {"id": mid, "viewBox": "0 0 10 10", "refX": "10", "refY": "5", "markerWidth": "5",
                         "markerHeight": "5", "orient": "auto-start-reverse", "markerUnits": "strokeWidth"}.items():
                m.set(k, v)
            p = etree.SubElement(m, _q("path"))
            # flat front one stroke-width wide: covers the line end without a stub past the tip
            # and without poking into the target (E17)
            p.set("d", "M 0,0 L 10,4 L 10,6 L 0,10 z")
            p.set("style", f"fill:{color};stroke:none")
        return mid

    def add_connector(self, spec: dict[str, Any]) -> tuple[str, list[str]]:
        """A connector between two elements. Returns (id, warnings).

        Without from_side/to_side/via it is a native Inkscape connector (Inkscape routes it and
        keeps it attached, also in the GUI — E09b). With them it is *routed* by us (Inkscape 1.4
        ignores connection points — E17): the route spec is stored and recomputed after moves.
        Either way the path is a placeholder until Engine.sync."""
        unknown = set(spec) - CONNECTOR_KEYS
        if unknown:
            raise DocumentError(f"Unknown connector keys {sorted(unknown)}. Allowed: {sorted(CONNECTOR_KEYS)}")
        src, dst = spec.get("from"), spec.get("to")
        if not src or not dst:
            raise DocumentError("A connector needs 'from' and 'to' element ids.")
        if src == dst:
            raise DocumentError("A connector cannot connect an element to itself.")
        routed = any(spec.get(k) for k in ("from_side", "to_side", "via"))
        for k in ("from_side", "to_side"):
            if spec.get(k) not in (None, "auto", "top", "right", "bottom", "left"):
                raise DocumentError(f"{k} must be top/right/bottom/left/auto.")
        via = spec.get("via")
        if via is not None and (not isinstance(via, list) or any(len(p) != 2 for p in via)):
            raise DocumentError("via must be a list of [x, y] points.")
        warnings = []
        for end in (src, dst):
            if _local(self.get(end)) == "text" and not routed:
                warnings.append(f"{end!r} is text: Inkscape routes to its centre, so the line will overlap "
                                "the letters. Connect the shape behind the text, or give from_side/to_side.")
        routing = spec.get("routing", "straight")
        if routing not in ("straight", "elbow"):
            raise DocumentError("routing must be 'straight' or 'elbow'.")
        arrow = spec.get("arrow", "end")
        if arrow not in ("end", "start", "both", "none"):
            raise DocumentError("arrow must be end/start/both/none.")
        parent = self.layer(spec["layer"]) if spec.get("layer") else self.root
        cid = spec.get("id") or self._new_id("connector")
        if self._find(cid) is not None:
            raise DocumentError(f"Id {cid!r} already exists.")
        color = str(spec.get("stroke", "#000000"))
        style = {"fill": "none", "stroke": color,
                 "stroke-width": _num(spec.get("stroke_width", self.default_stroke_width()))}
        if routed:
            style["stroke-linejoin"] = "miter"  # clean corners, no notch (field report 2)
        if spec.get("stroke_dasharray"):
            style["stroke-dasharray"] = str(spec["stroke_dasharray"])
        if spec.get("opacity") is not None:
            style["opacity"] = _num(spec["opacity"])
        if arrow != "none":
            marker = f"url(#{self.arrow_marker(color)})"
            if arrow in ("end", "both"):
                style["marker-end"] = marker
            if arrow in ("start", "both"):
                style["marker-start"] = marker
        el = etree.SubElement(parent, _q("path"))
        el.set("id", cid)
        el.set("d", "M 0,0")
        el.set("style", format_style(style))
        if routed:
            el.set(ROUTE_ATTR, json.dumps({"from": src, "to": dst, "from_side": spec.get("from_side"),
                                           "to_side": spec.get("to_side"), "via": via, "routing": routing},
                                          separators=(",", ":")))
        else:
            el.set(_q("connector-type", INKSCAPE_NS), "orthogonal" if routing == "elbow" else "polyline")
            el.set(_q("connector-curvature", INKSCAPE_NS), "0")
            el.set(CONN_START, f"#{src}")
            el.set(CONN_END, f"#{dst}")
        if spec.get("label"):
            fs = spec.get("font_size", self.default_font_size() * 0.8)
            # a halo only helps a label that sits ON the line; beside it, it just shows on tinted backgrounds
            halo = spec.get("label_halo", "none" if spec.get("label_offset") else "#ffffff")
            lstyle = {"font-size": f"{_num(fs)}px", "text-anchor": "middle", "fill": spec.get("label_color", color)}
            if spec.get("font_family"):
                lstyle["font-family"] = spec["font_family"]
            if spec.get("font_weight"):
                lstyle["font-weight"] = str(spec["font_weight"])
            if halo and halo != "none":  # halo keeps a label readable where it crosses the line
                lstyle.update({"paint-order": "stroke", "stroke": halo, "stroke-width": _num(fs * 0.3),
                               "stroke-linejoin": "round"})
            t = etree.SubElement(parent, _q("text"))
            t.set("id", f"{cid}_label")
            t.set(LABEL_FOR, cid)
            if spec.get("label_position") is not None:
                t.set(LABEL_POS, _num(float(spec["label_position"])))
            if spec.get("label_offset"):
                t.set(LABEL_OFFSET, _num(abs(float(spec["label_offset"]))))
            if spec.get("label_side", "auto") not in ("auto", "above", "below", "left", "right"):
                raise DocumentError("label_side must be auto/above/below/left/right.")
            t.set(LABEL_SIDE, spec.get("label_side", "auto"))
            t.set("style", format_style(lstyle))
            t.text = str(spec["label"])
        return cid, warnings

    def place_connector_labels(self) -> None:
        """Place each connector label on its route (pure lxml, run after routing): at label_position
        (fraction of the length; default: middle of the longest segment, never on a corner), moved
        label_offset towards label_side (above/below/left/right; auto = above horizontal segments,
        right of vertical ones) and anchored so the text sits beside the line. Cap height uses the
        default-sans metric (S4), no measuring."""
        from .layout import polyline_at, polyline_points

        for lab in self.root.xpath("//*[@inksmcp:label-for]", namespaces={"inksmcp": INKSMCP_NS}):
            conn = self._find(lab.get(LABEL_FOR))
            if conn is None:
                continue
            try:
                pts = polyline_points(conn.get("d", ""))
            except ValueError:
                continue
            if len(pts) < 2:
                continue
            pos = lab.get(LABEL_POS)
            x, y, angle = polyline_at(pts, float(pos) if pos is not None else None)
            offset = abs(float(lab.get(LABEL_OFFSET, "0")))
            side = lab.get(LABEL_SIDE, "auto")
            if side == "auto":  # above horizontal segments, right of vertical ones
                side = "above" if abs(math.cos(angle)) >= abs(math.sin(angle)) else "right"
            nx, ny = {"above": (0, -1), "below": (0, 1), "left": (-1, 0), "right": (1, 0)}[side]
            style = parse_style(lab.get("style"))
            fs = parse_length(style.get("font-size", "0"))
            cap = (fs[0] if fs else 0) * CAP_HEIGHT_EM * 2
            if offset:
                x, y = x + nx * offset, y + ny * offset
                style["text-anchor"] = "start" if nx > 0.3 else "end" if nx < -0.3 else "middle"
                baseline = y if ny < -0.3 else y + cap if ny > 0.3 else y + cap / 2
            else:
                style["text-anchor"] = "middle"
                baseline = y + cap / 2
            lab.set("style", format_style(style))
            lab.set("x", _num(round(x, 4)))
            lab.set("y", _num(round(baseline, 4)))

    TEXT_STYLE = {"font_size", "font_family", "font_weight", "font_style", "text_anchor"}

    @classmethod
    def accepts(cls, kind: str | None, key: str) -> bool:
        """Whether a `defaults` key applies to this element type (font keys only to text/groups)."""
        if kind not in GEOMETRY:
            return False
        if key in cls.TEXT_STYLE:
            return kind in ("text", "group")
        return key in COMMON or key in GEOMETRY[kind] or key in STYLE_KEYS

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
        if spec.get("vertical_anchor", "baseline") not in VERTICAL_ANCHORS:
            raise DocumentError(f"vertical_anchor must be one of {VERTICAL_ANCHORS}.")
        for key in GEOMETRY[kind]:
            if (key not in spec or key in NON_ATTR_KEYS or kind == "arrow"
                    or (kind == "text" and key in TEXT_NON_ATTR_KEYS)):
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
        for key, css in (("marker_start", "marker-start"), ("marker_end", "marker-end")):
            if key in spec:
                if spec[key] == "arrow":
                    style[css] = f"url(#{self.arrow_marker(style.get('stroke', '#000000'))})"
                elif spec[key] in ("none", None):
                    style.pop(css, None)
                else:
                    raise DocumentError(f"{key} must be 'arrow' or 'none'.")
        if kind == "arrow":
            self._arrow_geometry(el, spec)
        if kind == "text" and "width" in spec:
            if spec["width"]:
                if float(spec["width"]) <= 0:
                    raise DocumentError("width must be > 0.")
                el.set(WRAP_ATTR, _num(float(spec["width"])))
            else:
                el.attrib.pop(WRAP_ATTR, None)
        if style:
            el.set("style", format_style(style))
        if kind == "text":
            lines = [c for c in el if _local(c) == "tspan" and c.get(_q("role", SODIPODI_NS)) == "line"]
            if "text" in spec:
                el.attrib.pop(PARA_ATTR, None)  # new source text for wrapping
                self._set_text(el, str(spec["text"]), spec.get("line_height"))
            elif lines and ({"x", "y", "font_size", "line_height", "style"} & set(spec)):
                # re-lay out existing lines (explicit tspan y must follow x/y/size changes)
                self._set_text(el, "\n".join("".join(c.itertext()) for c in lines), spec.get("line_height"))

    ARROW_KEYS = ("x1", "y1", "x2", "y2", "shaft_width", "head_width", "head_length")

    def _arrow_geometry(self, el: etree._Element, spec: dict[str, Any]) -> None:
        """Block arrow from (x1, y1) to the tip (x2, y2) as a filled path (field report 2)."""
        import math

        stored = dict(zip(self.ARROW_KEYS, (float(v) for v in el.get(ARROW_ATTR, "").split(",") if v)))
        p = {**stored, **{k: float(spec[k]) for k in self.ARROW_KEYS if k in spec}}
        missing = [k for k in ("x1", "y1", "x2", "y2") if k not in p]
        if missing:
            raise DocumentError(f"arrow needs {missing}.")
        length = math.hypot(p["x2"] - p["x1"], p["y2"] - p["y1"])
        if length == 0:
            raise DocumentError("arrow start and tip must differ.")
        sw = p.get("shaft_width", length * 0.12)
        hw = p.get("head_width", sw * 2.5)
        hl = min(p.get("head_length", hw * 0.9), length)
        p.update(shaft_width=sw, head_width=hw, head_length=hl)
        ux, uy = (p["x2"] - p["x1"]) / length, (p["y2"] - p["y1"]) / length
        nx, ny = -uy, ux

        def pt(along: float, across: float) -> str:
            return f"{_num(round(p['x1'] + ux * along + nx * across, 4))},{_num(round(p['y1'] + uy * along + ny * across, 4))}"

        b = length - hl
        el.set("d", "M " + " L ".join([pt(0, sw / 2), pt(b, sw / 2), pt(b, hw / 2), pt(length, 0),
                                        pt(b, -hw / 2), pt(b, -sw / 2), pt(0, -sw / 2)]) + " Z")
        el.set(ARROW_ATTR, ",".join(_num(round(p[k], 4)) for k in self.ARROW_KEYS))

    def text_of(self, el: etree._Element) -> str:
        """The text as the agent wrote it (lines joined by newlines; wrapping undone)."""
        if el.get(PARA_ATTR) is not None:
            return el.get(PARA_ATTR)
        lines = [c for c in el if _local(c) == "tspan"]
        return "\n".join("".join(c.itertext()) for c in lines) if lines else (el.text or "")

    def set_wrapped(self, el: etree._Element, source: str, lines: list[str]) -> None:
        el.set(PARA_ATTR, source)
        self._set_text(el, "\n".join(lines))

    def _font_size(self, el: etree._Element) -> float:
        """Effective font size in user units (inherited), for laying out lines."""
        e = el
        while e is not None and isinstance(e.tag, str):
            fs = parse_length(parse_style(e.get("style")).get("font-size"))
            if fs and fs[1] == "px":
                return fs[0]
            e = e.getparent()
        return self.default_font_size()

    def _set_text(self, el: etree._Element, text: str, line_height: float | None = None) -> None:
        """Multi-line text as sodipodi:role="line" tspans with line-height in the style AND an
        explicit y per line: Inkscape double-counts dy on role=line tspans (E17), and browsers
        ignore sodipodi:role, so explicit y is the one layout both agree on."""
        style = parse_style(el.get("style"))
        if line_height is None:
            try:
                line_height = float(style.get("line-height", 1.25))
            except ValueError:
                line_height = 1.25
        for child in list(el):
            el.remove(child)
        el.text = None
        lines = text.split("\n")
        if any(l != l.strip() or "  " in l for l in lines):
            el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")  # keep indents (field report 2)
        if len(lines) == 1:
            el.text = text
            return
        style["line-height"] = _num(line_height)
        el.set("style", format_style(style))
        x = el.get("x", "0")
        y0 = float(el.get("y", "0"))
        step = line_height * self._font_size(el)
        for i, line in enumerate(lines):
            t = etree.SubElement(el, _q("tspan"))
            t.set("id", self._new_id("tspan"))
            t.set(_q("role", SODIPODI_NS), "line")
            t.set("x", x)
            t.set("y", _num(round(y0 + i * step, 4)))
            t.text = line

    # -- inspection ------------------------------------------------------
    def outline(self, bboxes: dict[str, tuple[float, float, float, float]] | None = None,
                max_depth: int = 6, max_children: int = 40, root: etree._Element | None = None) -> list[dict[str, Any]]:
        """Compact, agent-friendly tree of drawable elements. Containers with more than
        `max_children` children are summarised (counts per type, first/last ids, overall bbox)
        so one big grid doesn't flood the agent's context (E14: 325 lines = 30k chars)."""

        def summary(el: etree._Element) -> dict[str, Any]:
            kids = [c for c in el if isinstance(c.tag, str) and _local(c) in SHAPE_TAGS]
            types: dict[str, int] = {}
            for c in kids:
                types[_local(c)] = types.get(_local(c), 0) + 1
            return {"children_count": len(kids), "types": types,
                    "first_ids": [c.get("id") for c in kids[:3]], "last_ids": [c.get("id") for c in kids[-3:]]}

        def node(el: etree._Element, depth: int) -> dict[str, Any] | None:
            tag = _local(el)
            if tag not in SHAPE_TAGS:
                return None
            is_layer = tag == "g" and el.get(_q("groupmode", INKSCAPE_NS)) == "layer"
            d: dict[str, Any] = {"id": el.get("id"), "type": "layer" if is_layer else ("group" if tag == "g" else tag)}
            if el.get(CONN_START) or el.get(CONN_END) or el.get(ROUTE_ATTR) is not None:
                d["type"] = "connector"
                d["from"], d["to"] = self.connector_ends(el)
            if el.get(LABEL_FOR):
                d["label_for"] = el.get(LABEL_FOR)
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
            if tag == "g":
                n_kids = sum(1 for c in el if isinstance(c.tag, str) and _local(c) in SHAPE_TAGS)
                if depth < max_depth and n_kids <= max_children:
                    d["children"] = [n for n in (node(c, depth + 1) for c in el) if n]
                else:
                    d.update(summary(el))
            return d

        start = self.root if root is None else root
        kids = [c for c in start if isinstance(c.tag, str) and _local(c) in SHAPE_TAGS]
        loose = [c for c in kids if _local(c) != "g"]
        if len(loose) <= max_children:
            return [n for n in (node(c, 0) for c in kids) if n]
        # many loose elements (no layers): keep containers, summarise the rest
        out = [n for n in (node(c, 0) for c in kids if _local(c) == "g") if n]
        s = summary(start)
        s.update({"type": "summary", "note": "loose elements not in a layer/group; inspect with a larger max_children"})
        s["types"].pop("g", None)
        s["children_count"] = len(loose)
        s["first_ids"] = [c.get("id") for c in loose[:3]]
        s["last_ids"] = [c.get("id") for c in loose[-3:]]
        return out + [s]

    # -- stacking order -------------------------------------------------
    def _ctm(self, el: etree._Element | None):
        """Transform from `el`'s coordinates to the root's user units (root viewBox excluded)."""
        from .layout import IDENTITY, mat_mul, parse_transform

        chain = []
        while el is not None and el is not self.root:
            chain.append(el)
            el = el.getparent()
        m = IDENTITY
        for e in reversed(chain):
            m = mat_mul(m, parse_transform(e.get("transform")))
        return m

    def _ordered(self, ids: list[str]) -> list[etree._Element]:
        els = [self.get(i) for i in dict.fromkeys(ids)]
        pos = {e: n for n, e in enumerate(self.root.iter())}
        return sorted(els, key=pos.__getitem__)  # keep their relative document order

    def reparent(self, el: etree._Element, parent: etree._Element, index: int | None = None) -> None:
        """Move `el` under `parent` at `index` (None = on top), keeping its visual position."""
        from .layout import format_transform, mat_inv, mat_mul, parse_transform

        old_parent = el.getparent()
        if parent is not old_parent and not (el.get(CONN_START) or el.get(CONN_END) or el.get(ROUTE_ATTR)):
            # connectors are re-routed instead (F20)
            local = mat_mul(mat_mul(mat_inv(self._ctm(parent)), self._ctm(old_parent)),
                            parse_transform(el.get("transform")))
            t = format_transform(local)
            if t:
                el.set("transform", t)
            else:
                el.attrib.pop("transform", None)
        old_parent.remove(el)
        if index is None:
            parent.append(el)
        else:
            parent.insert(index, el)

    def z_order(self, ids: list[str], op: str, target: str | None = None) -> None:
        """front/back: top/bottom of each element's own parent. above/below: directly above/below
        `target`, moving into its parent (layer/group) if needed."""
        els = self._ordered(ids)
        if op in ("front", "back"):
            groups: dict[etree._Element, list] = {}
            for e in els:
                groups.setdefault(e.getparent(), []).append(e)
            for parent, members in groups.items():
                for n, e in enumerate(members):
                    parent.remove(e)
                    if op == "front":
                        parent.append(e)
                    else:
                        parent.insert(n, e)
            return
        if op not in ("above", "below"):
            raise DocumentError(f"Unknown z-order operation {op!r}.")
        if not target:
            raise DocumentError(f"'{op}' needs a target id.")
        tgt = self.get(target)
        for e in els:
            if e is tgt or tgt in e.iterdescendants() or e in tgt.iterancestors():
                raise DocumentError(f"Cannot move {e.get('id')!r} {op} {target!r}: one contains the other.")
        parent = tgt.getparent()
        for e in (els if op == "below" else reversed(els)):
            if e.getparent() is parent:  # same parent: plain reorder, no transform change
                parent.remove(e)
                idx = list(parent).index(tgt)
                parent.insert(idx if op == "below" else idx + 1, e)
            else:
                idx = list(parent).index(tgt)
                self.reparent(e, parent, idx if op == "below" else idx + 1)

    def move_to(self, ids: list[str], container: str, position: str = "top") -> etree._Element:
        """Move elements (keeping their order and visual position) into a layer — by name,
        created if missing — or into a group/layer given by id; on top of it or at its bottom."""
        if position not in ("top", "bottom"):
            raise DocumentError("position must be 'top' or 'bottom'.")
        found = self._find(container)
        if found is not None and _local(found) != "g":
            raise DocumentError(f"{container!r} is a {_local(found)}, not a layer or group.")
        dest = found if found is not None else self.layer(container)
        for n, e in enumerate(self._ordered(ids)):
            if e is dest or dest in e.iterdescendants():
                raise DocumentError(f"Cannot move {e.get('id')!r} into itself.")
            if e.getparent() is dest:
                dest.remove(e)
                dest.insert(n, e) if position == "bottom" else dest.append(e)
            else:
                self.reparent(e, dest, n if position == "bottom" else None)
        return dest

    def stack_position(self, id_: str) -> dict[str, Any]:
        el = self.get(id_)
        parent = el.getparent()
        siblings = [c for c in parent if isinstance(c.tag, str) and _local(c) in SHAPE_TAGS]
        return {"parent": parent.get("id"), "index": siblings.index(el), "of": len(siblings)}

    TIDY_ATTRS =("x", "y", "cx", "cy", "x1", "y1", "x2", "y2", "width", "height", "r", "rx", "ry", "transform")

    def tidy_numbers(self, ids: list[str], decimals: int = 4) -> None:
        """Round geometry numbers on `ids` and their descendants. Inkscape writes ~8 significant
        digits after px conversions, e.g. 81.405006 for 81.405 (F14)."""
        def fix(m: re.Match) -> str:
            v = round(float(m.group(0)), decimals)
            return _num(0.0 if v == 0 else v)

        for id_ in ids:
            el = self._find(id_)
            if el is None:
                continue
            for e in el.iter():
                if not isinstance(e.tag, str):
                    continue
                for attr in self.TIDY_ATTRS:
                    val = e.get(attr)
                    if val and not val.endswith("%"):
                        e.set(attr, re.sub(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?", fix, val))

    def ids(self) -> list[str]:
        return [el.get("id") for el in self.root.iter() if isinstance(el.tag, str) and el.get("id")]
