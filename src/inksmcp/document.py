"""Domain layer: an SVG document the agent edits through intent-level element specs.

All coordinates are in document *user units* (the unit the document was created with).
Styles are always written to the `style` attribute: Inkscape drops presentation
attributes like fill="..." on boolean ops (experiment E03).
"""
from __future__ import annotations

import copy
import gzip
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
for _prefix, _uri in (("inksmcp", INKSMCP_NS), ("sodipodi", SODIPODI_NS), ("inkscape", INKSCAPE_NS)):
    etree.register_namespace(_prefix, _uri)

CONN_START = f"{{{INKSCAPE_NS}}}connection-start"
CONN_END = f"{{{INKSCAPE_NS}}}connection-end"
LABEL_FOR = f"{{{INKSMCP_NS}}}label-for"
ARROW_ATTR = f"{{{INKSMCP_NS}}}arrow"  # block arrow parameters, so updates can regenerate the path
WRAP_ATTR = f"{{{INKSMCP_NS}}}wrap-width"  # text wraps to this width (user units)
PARA_ATTR = f"{{{INKSMCP_NS}}}paragraphs"  # the unwrapped text, so re-wrapping never loses breaks
CAP_HEIGHT_EM = 0.357  # half the default sans cap height (S4) — centres a label on a point without measuring
ROUTE_ATTR = f"{{{INKSMCP_NS}}}route"  # JSON route spec of connectors we route ourselves (sides/via)
GRID_ATTR = f"{{{INKSMCP_NS}}}grid"  # JSON axes of a grid, so `plot` can map data values
SRC_ATTR = f"{{{INKSMCP_NS}}}src"  # the file an image came from (its href may be a data URI)
PLACE_ATTR = f"{{{INKSMCP_NS}}}place"  # JSON {side, ref, gap, align}: kept beside another element (step 2)
CLIP_ATTR = f"{{{INKSMCP_NS}}}clip"  # marks clipPaths made by the `clip` key (what they were made from)
USE_ATTR = f"{{{INKSMCP_NS}}}use-size"  # JSON {x, y, w, h, scale}: a use the engine sizes (no viewBox, N1)
FIT_ATTR = f"{{{INKSMCP_NS}}}fit"  # JSON {ids, padding, fit}: a rect sized to other elements (field report 3)
LABEL_POS = f"{{{INKSMCP_NS}}}label-position"
LABEL_OFFSET = f"{{{INKSMCP_NS}}}label-offset"
LABEL_SIDE = f"{{{INKSMCP_NS}}}label-side"
CONNECTOR_KEYS = {"from", "to", "id", "routing", "arrow", "stroke", "stroke_width", "stroke_dasharray",
                  "opacity", "layer", "label", "font_size", "label_color", "from_side", "to_side", "via",
                  "label_position", "label_offset", "label_side", "label_halo", "font_family", "font_weight",
                  "start_gap", "end_gap"}

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
    "rect": ("x", "y", "width", "height", "rx", "ry", "fit_to", "fit_padding", "fit"),
    "circle": ("cx", "cy", "r"),
    "ellipse": ("cx", "cy", "rx", "ry"),
    "line": ("x1", "y1", "x2", "y2", "marker_start", "marker_end"),
    "polyline": ("points", "marker_start", "marker_end"),
    "polygon": ("points",),
    "path": ("d", "marker_start", "marker_end"),
    "text": ("x", "y", "text", "line_height", "vertical_anchor", "width", "halo", "halo_width"),
    "group": (),
    "arrow": ("x1", "y1", "x2", "y2", "shaft_width", "head_width", "head_length"),
    "image": ("x", "y", "width", "height", "href", "object_fit", "embed"),
    "use": ("x", "y", "width", "height", "href"),
}
# spec keys that are not written as same-named SVG attributes
NON_ATTR_KEYS = {"marker_start", "marker_end", "fit_to", "fit_padding", "fit", "href", "object_fit", "embed"}
OBJECT_FIT = {"contain": "xMidYMid meet", "cover": "xMidYMid slice", "fill": "none"}  # E25
TEXT_NON_ATTR_KEYS = {"text", "line_height", "vertical_anchor", "width", "halo", "halo_width"}
COMMON = {"type", "id", "label", "layer", "parent", "transform", "style", "clip", "place"}
PLACE_SIDES = ("below", "above", "left_of", "right_of")
HALO_CSS = ("paint-order", "stroke", "stroke-width", "stroke-linejoin")
# where `y` sits on a text: baseline (SVG default), cap top, cap middle, or baseline of the last line
VERTICAL_ANCHORS = ("baseline", "top", "middle", "bottom")

SHAPE_TAGS = {"rect", "circle", "ellipse", "line", "polyline", "polygon", "path", "text", "g", "image", "use",
              "flowRoot"}
# properties children inherit; on a foreign root they would also style every element we add (E30)
INHERITED = ("fill", "fill-opacity", "fill-rule", "stroke", "stroke-width", "stroke-opacity", "stroke-linecap",
             "stroke-linejoin", "stroke-miterlimit", "stroke-dasharray", "stroke-dashoffset", "font-family",
             "font-size", "font-weight", "font-style", "text-anchor", "color")
NOT_DRAWN = {"defs", "namedview", "metadata", "title", "desc", "style", "script"}


_NAMED = {"black": "#000000", "white": "#ffffff", "red": "#ff0000", "green": "#008000", "blue": "#0000ff",
          "yellow": "#ffff00", "gray": "#808080", "grey": "#808080", "orange": "#ffa500", "none": "none"}


def norm_color(v: str | None) -> str | None:
    """#rgb, #rrggbb, rgb(r,g,b), rgb(%,%,%) and a few names -> #rrggbb, so colours written differently match."""
    if v is None:
        return None
    v = v.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{3}", v):
        return "#" + "".join(c * 2 for c in v[1:])
    if re.fullmatch(r"#[0-9a-f]{6}", v):
        return v
    m = re.fullmatch(r"rgb\(\s*([\d.]+)(%?)\s*,\s*([\d.]+)(%?)\s*,\s*([\d.]+)(%?)\s*\)", v)
    if m:
        vals = [float(m.group(i)) * (2.55 if m.group(i + 1) else 1) for i in (1, 3, 5)]
        return "#" + "".join(f"{max(0, min(255, round(x))):02x}" for x in vals)
    return _NAMED.get(v, v)


_URL_REF = re.compile(r"url\(#([^)]+)\)")


def refs_in(el: etree._Element) -> set[str]:
    """Ids referenced from el and its descendants: url(#x) in any attribute or style, and #x hrefs."""
    out: set[str] = set()
    for e in el.iter():
        if not isinstance(e.tag, str):
            continue
        for v in e.attrib.values():
            if v.startswith("#") and " " not in v:
                out.add(v[1:])
            elif "url(#" in v:
                out.update(_URL_REF.findall(v))
    return out


def read_svg_bytes(data: bytes) -> bytes:
    """.svgz is gzip-compressed SVG (field report: edit-existing-svgs)."""
    return gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data


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
        self.notes: list[str] = []
        self.pruned: list[str] = []  # defs removed by delete() since the caller last cleared this
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
        """Open a file (.svg or .svgz) and normalise its page (see `normalise`); `notes` says what changed."""
        path = Path(path)
        if not path.exists():
            raise DocumentError(f"File not found: {path}")
        data = path.read_bytes()
        parser = etree.XMLParser(remove_blank_text=False, huge_tree=True, resolve_entities=False)
        try:
            raw = etree.fromstring(read_svg_bytes(data), parser)
        except (etree.XMLSyntaxError, OSError, EOFError) as e:
            raise DocumentError(f"{path.name} is not a readable SVG file: {e}") from e
        missing = [el for el in raw.iter() if isinstance(el.tag, str) and el.get("id") is None
                   and _local(el) in SHAPE_TAGS | {"tspan"}]
        doc = cls.from_bytes(data, path)
        doc.notes = doc.normalise()
        if missing:
            had = {el.get("id") for el in raw.iter() if isinstance(el.tag, str)}
            given = [el.get("id") for el in doc.root.iter() if isinstance(el.tag, str) and el.get("id") not in had]
            doc.notes.append(f"{len(missing)} elements had no id and were given one ({', '.join(given[:3])}, ...); saving writes them to the file, so they stay the same "
                             "next time. import_file of the same file assigns the same ids.")
        return doc

    def normalise(self) -> list[str]:
        """Bring a foreign page into the form every tool assumes: viewBox origin 0,0, one uniform scale
        from user units to the page, and no paint inherited from the root. Rendering is unchanged (E30):
        - width/height "100%" or missing are read as the viewBox size, as Inkscape does;
        - a viewBox whose aspect differs from the page is scaled uniformly and aligned (preserveAspectRatio,
          default xMidYMid meet); that offset (and a non-zero origin, or a "none" stretch) moves onto the
          top-level elements' transforms and the viewBox becomes the whole page;
        - fill/stroke/font properties set on the root move onto its top-level elements (and defs).
        Returns notes for the agent."""
        notes: list[str] = []
        r = self.root
        lengths = [parse_length(r.get(k)) for k in ("width", "height")]
        absolute = [L[0] * PX_PER_UNIT[L[1]] if L and L[1] in PX_PER_UNIT else None for L in lengths]
        vb_attr = r.get("viewBox")
        try:
            vb = [float(v) for v in re.split(r"[\s,]+", vb_attr.strip())] if vb_attr else None
        except ValueError:
            vb = None
        if vb is None or len(vb) != 4 or vb[2] <= 0 or vb[3] <= 0:
            if None in absolute:
                return notes  # nothing to anchor a page to; leave it as it is
            vb = [0.0, 0.0, absolute[0], absolute[1]]
            r.set("viewBox", f"0 0 {_num(round(vb[2], 4))} {_num(round(vb[3], 4))}")
            notes.append(f"No viewBox: user units are px (added viewBox 0 0 {_num(round(vb[2], 4))} "
                         f"{_num(round(vb[3], 4))}).")
        vbx, vby, vbw, vbh = vb
        wv = absolute[0] if absolute[0] is not None else vbw  # "100%" / missing -> viewBox size (E30 B)
        hv = absolute[1] if absolute[1] is not None else vbh
        sx, sy = wv / vbw, hv / vbh

        def close(a: float, b: float) -> bool:  # page sizes are written rounded (page_fit: 4 decimals, N4)
            return abs(a - b) <= 1e-6 * max(abs(a), abs(b), 1e-9)

        if close(sx, sy):
            sy = sx
        par = (r.get("preserveAspectRatio") or "xMidYMid meet").split()
        if par[0] == "none":
            s, kx, ky, ox, oy = sx, 1.0, sy / sx, 0.0, 0.0
        else:
            s = max(sx, sy) if par[-1] == "slice" else min(sx, sy)
            ax = {"xMin": 0.0, "xMid": 0.5, "xMax": 1.0}.get(par[0][:4], 0.5)
            ay = {"YMin": 0.0, "YMid": 0.5, "YMax": 1.0}.get(par[0][4:], 0.5)
            kx = ky = 1.0
            ox, oy = (wv - vbw * s) * ax, (hv - vbh * s) * ay
        tx, ty = ox / s - vbx * kx, oy / s - vby * ky
        tiny = 1e-6 * max(vbw, vbh)
        if abs(tx) <= tiny and abs(ty) <= tiny:
            tx = ty = 0.0
        stretched = abs(kx - 1) > 1e-9 or abs(ky - 1) > 1e-9
        changed_page = (any(a is None for a in absolute) or stretched or tx != 0 or ty != 0
                        or not close(wv / s, vbw) or not close(hv / s, vbh))
        if changed_page:
            prefix = []
            if abs(tx) > 1e-9 or abs(ty) > 1e-9:
                prefix.append(f"translate({tx:.10g},{ty:.10g})")
            if stretched:
                prefix.append(f"scale({kx:.10g},{ky:.10g})")
            moved = []
            if prefix:
                for el in r:
                    if isinstance(el.tag, str) and _local(el) not in NOT_DRAWN:
                        old = el.get("transform")
                        el.set("transform", " ".join(prefix + ([old] if old else [])))
                        moved.append(el.get("id") or _local(el))
            new_w, new_h = wv / s, hv / s
            r.set("viewBox", f"0 0 {new_w:.10g} {new_h:.10g}")
            for k, v, L in (("width", wv, lengths[0]), ("height", hv, lengths[1])):
                if not L or L[1] not in PX_PER_UNIT:
                    r.set(k, _num(round(v, 4)))
            if "preserveAspectRatio" in r.attrib:
                del r.attrib["preserveAspectRatio"]
            what = []
            if any(a is None for a in absolute):
                what.append("width/height given as % or missing were read as the viewBox size (as Inkscape does)")
            if stretched:
                what.append('preserveAspectRatio="none" stretched the drawing')
            elif abs(ox) > 1e-9 or abs(oy) > 1e-9:
                what.append("the viewBox did not match the page's shape, so the drawing sat centred with empty bands")
            if abs(vbx) > 1e-9 or abs(vby) > 1e-9:
                what.append("the viewBox did not start at 0,0")
            notes.append("Page normalised, rendering unchanged: " + "; ".join(what)
                         + f". The viewBox is now 0 0 {_num(round(new_w, 3))} {_num(round(new_h, 3))}"
                         + (f" and {len(moved)} top-level element(s) got {' '.join(prefix)} in front of their "
                            "transform" if moved else "") + ".")
        # paint set on the root would be inherited by everything we add
        style = parse_style(r.get("style"))
        props = {k: r.get(k) for k in INHERITED if r.get(k) is not None}
        props.update({k: v for k, v in style.items() if k in INHERITED})
        if props:
            for el in r:
                if not isinstance(el.tag, str) or _local(el) in NOT_DRAWN - {"defs"}:
                    continue
                st = parse_style(el.get("style"))
                add = {k: v for k, v in props.items() if k not in st and el.get(k) is None}
                if add:
                    el.set("style", format_style({**add, **st}))
            for k in props:
                if k in r.attrib:
                    del r.attrib[k]
            rest = {k: v for k, v in style.items() if k not in INHERITED}
            if rest:
                r.set("style", format_style(rest))
            elif "style" in r.attrib:
                del r.attrib["style"]
            notes.append("The root set " + "; ".join(f"{k}:{v}" for k, v in props.items())
                         + " for everything: moved onto its top-level elements, so new elements don't inherit it.")
        return notes

    @classmethod
    def from_bytes(cls, data: bytes, path: Path | None = None) -> "Document":
        parser = etree.XMLParser(remove_blank_text=False, huge_tree=True, resolve_entities=False)
        try:
            root = etree.fromstring(read_svg_bytes(data), parser)
        except (etree.XMLSyntaxError, OSError, EOFError) as e:
            raise DocumentError(f"{path.name if path else 'The data'} is not a readable SVG file: {e}") from e
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
        self.root.set(_q("docname", SODIPODI_NS), target.name)
        data = self.to_bytes()
        target.write_bytes(gzip.compress(data) if target.suffix.lower() == ".svgz" else data)
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
        """The length one user unit stands for: the width's unit when that is what the viewBox gives,
        else any unit that matches (no viewBox: px), else "user" (see px_per_user_unit)."""
        s = self.px_per_user_unit
        w = parse_length(self.root.get("width"))
        order = ([w[1]] if w and w[1] in PX_PER_UNIT else []) + list(PX_PER_UNIT)
        return next((u for u in order if abs(PX_PER_UNIT[u] - s) <= 1e-6 * s), "user")

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
        used = refs_in(el)
        el.getparent().remove(el)
        removed = [id_]
        for conn in self.connectors():
            if set(self.connector_ends(conn)) & gone:
                removed.append(conn.get("id"))
                used |= refs_in(conn)
                conn.getparent().remove(conn)
                gone.add(conn.get("id"))
        for lab in self.root.xpath("//*[@inksmcp:label-for]", namespaces={"inksmcp": INKSMCP_NS}):
            if lab.get(LABEL_FOR) in gone:
                removed.append(lab.get("id"))
                lab.getparent().remove(lab)
        self.pruned += self.prune_defs(used - gone)
        return removed

    def prune_defs(self, candidates: set[str]) -> list[str]:
        """Remove defs (symbols, gradients, clip paths, markers...) among `candidates` that nothing references
        any more, and then what only they referenced (field report: edit-existing-svgs, imported libraries).
        Defs that were unused before are left alone."""
        removed: list[str] = []
        while candidates:
            used = refs_in(self.root)
            nxt: set[str] = set()
            for c in sorted(candidates):
                el = self._find(c)
                if el is None or c in used or not any(_local(a) == "defs" for a in el.iterancestors()):
                    continue
                nxt |= refs_in(el)
                el.getparent().remove(el)
                removed.append(c)
            candidates = nxt - set(removed)
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
            m = etree.SubElement(self._defs(), _q("marker"))
            for k, v in {"id": mid, "viewBox": "0 0 10 10", "refX": "10", "refY": "5", "markerWidth": "5",
                         "markerHeight": "5", "orient": "auto-start-reverse", "markerUnits": "strokeWidth"}.items():
                m.set(k, v)
            p = etree.SubElement(m, _q("path"))
            # flat front one stroke-width wide: covers the line end without a stub past the tip
            # and without poking into the target (E17)
            p.set("d", "M 0,0 L 10,4 L 10,6 L 0,10 z")
            p.set("style", f"fill:{color};stroke:none")
        return mid

    def _connector_layer(self, src: str, dst: str) -> etree._Element:
        """The layer both ends are in, else a "Connectors" layer (field report 9: connectors at the
        document root showed up as loose elements)."""
        def top_layer(id_: str):
            el = self.get(id_)
            return next((a for a in [el, *el.iterancestors()] if a in self.layers()), None)

        a, b = top_layer(src), top_layer(dst)
        return a if a is not None and a is b else self.layer("Connectors")

    def _defs(self) -> etree._Element:
        defs = next((c for c in self.root if _local(c) == "defs"), None)
        if defs is None:
            defs = etree.Element(_q("defs"))
            defs.set("id", self._new_id("defs"))
            self.root.insert(0, defs)
        return defs

    def _set_clip(self, el: etree._Element, clip: Any) -> None:
        """clip: an element id (its shape, as it is now) or [x, y, w, h] in the element's parent
        coordinates. The shape is copied into a clipPath in the element's own coordinates
        (inv(CTM(el)) . CTM(source)), so it moves with the element afterwards (E24)."""
        from .layout import format_transform, mat_inv, mat_mul

        old = el.get("clip-path", "")
        m = re.fullmatch(r"url\(#(.+)\)", old)
        if m and self._find(m.group(1)) is not None and self._find(m.group(1)).get(CLIP_ATTR):
            cp = self._find(m.group(1))
            cp.getparent().remove(cp)  # ours: replaced, not accumulated
        el.attrib.pop("clip-path", None)
        if clip in (None, "", "none"):
            return
        if isinstance(clip, str):
            src = self.get(clip)
            if src is el or el in src.iterancestors():
                raise DocumentError(f"clip {clip!r}: an element cannot be clipped by itself or its ancestor.")
            if _local(src) not in SHAPE_TAGS:
                raise DocumentError(f"clip {clip!r} is not a shape.")
            shape = copy.deepcopy(src)
            space = src
        elif isinstance(clip, (list, tuple)) and len(clip) == 4 and all(isinstance(v, (int, float)) for v in clip):
            if clip[2] <= 0 or clip[3] <= 0:
                raise DocumentError("clip rect needs a positive width and height.")
            shape = etree.Element(_q("rect"))
            for k, v in zip(("x", "y", "width", "height"), clip):
                shape.set(k, _num(v))
            space = el.getparent()
        else:
            raise DocumentError("clip must be an element id, [x, y, width, height] or null.")
        for node in shape.iter():
            if isinstance(node.tag, str):
                for a in ("id", "style", "clip-path", "transform") if node is shape else ("id",):
                    node.attrib.pop(a, None)
        t = format_transform(mat_mul(mat_inv(self._ctm(el)), self._ctm(space)))
        if t:
            shape.set("transform", t)
        cp = etree.SubElement(self._defs(), _q("clipPath"))
        cp.set("id", self.free_id(f"{el.get('id')}-clip"))
        cp.set("clipPathUnits", "userSpaceOnUse")
        cp.set(CLIP_ATTR, clip if isinstance(clip, str) else ",".join(_num(v) for v in clip))
        cp.append(shape)
        el.set("clip-path", f"url(#{cp.get('id')})")

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
        # gaps need our routing: Inkscape re-routes native connectors on every load, export included (F15)
        routed = any(spec.get(k) for k in ("from_side", "to_side", "via", "start_gap", "end_gap"))
        for k in ("start_gap", "end_gap"):
            if spec.get(k) is not None and float(spec[k]) < 0:
                raise DocumentError(f"{k} must be >= 0.")
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
        parent = self.layer(spec["layer"]) if spec.get("layer") else self._connector_layer(src, dst)
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
                                           "to_side": spec.get("to_side"), "via": via, "routing": routing,
                                           "start_gap": spec.get("start_gap"), "end_gap": spec.get("end_gap")},
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
        if kind == "image":
            self._image(el, spec)
        if kind == "use":
            for k, v in (self._use(el, spec) if "href" in spec else {}).items():
                style.setdefault(k, v)
            self._use_size(el, spec)
        if kind == "text" and ("halo" in spec or "halo_width" in spec):
            self._set_halo(el, style, spec)
        if kind == "rect" and {"fit_to", "fit_padding", "fit"} & set(spec):
            self._set_fit(el, spec)
        if kind == "text" and "width" in spec:
            if spec["width"]:
                if float(spec["width"]) <= 0:
                    raise DocumentError("width must be > 0.")
                el.set(WRAP_ATTR, _num(float(spec["width"])))
            else:
                el.attrib.pop(WRAP_ATTR, None)
        if style:
            el.set("style", format_style(style))
        if "clip" in spec:
            self._set_clip(el, spec["clip"])
        if "place" in spec:
            self._set_place(el, spec["place"])
        if kind == "text":
            lines = [c for c in el if _local(c) == "tspan" and c.get(_q("role", SODIPODI_NS)) == "line"]
            if "text" in spec:
                el.attrib.pop(PARA_ATTR, None)  # new source text for wrapping
                self._set_text(el, str(spec["text"]), spec.get("line_height"))
            elif lines and ({"x", "y", "font_size", "line_height", "style"} & set(spec)):
                # re-lay out existing lines (explicit tspan y must follow x/y/size changes)
                self._set_text(el, "\n".join("".join(c.itertext()) for c in lines), spec.get("line_height"))

    def _set_place(self, el: etree._Element, place: Any) -> None:
        """Store {"below"|"above"|"left_of"|"right_of": id, "gap": n, "align": start|center|end}; the engine
        moves the element there after measuring, and again whenever the reference changes."""
        if not place:
            el.attrib.pop(PLACE_ATTR, None)
            return
        if not isinstance(place, dict):
            raise DocumentError('place must be {"below": id, "gap": 2} (or above / left_of / right_of) or null.')
        sides = [k for k in PLACE_SIDES if k in place]
        unknown = set(place) - set(PLACE_SIDES) - {"gap", "align"}
        if len(sides) != 1 or unknown:
            raise DocumentError(f"place needs exactly one of {', '.join(PLACE_SIDES)} (plus gap, align); got {sorted(place)}.")
        ref = place[sides[0]]
        if not isinstance(ref, str) or not ref:
            raise DocumentError(f"place {sides[0]} must be an element id.")
        gap = place.get("gap", 0)
        if not isinstance(gap, (int, float)):
            raise DocumentError("place gap must be a number (user units).")
        if place.get("align") not in (None, "start", "center", "end"):
            raise DocumentError("place align must be start, center or end.")
        data = {"side": sides[0], "ref": ref, "gap": gap, **({"align": place["align"]} if place.get("align") else {})}
        el.set(PLACE_ATTR, json.dumps(data, separators=(",", ":")))

    def _set_halo(self, el: etree._Element, style: dict[str, str], spec: dict[str, Any]) -> None:
        """A background-coloured outline behind the glyphs (paint-order: stroke), so text stays
        readable over lines and artwork. Width defaults to 0.3 x font size; the measured bbox grows
        by the width (E24)."""
        color = spec.get("halo", "__keep__")
        if color in (None, "", "none"):
            for k in HALO_CSS:
                style.pop(k, None)
            return
        if color == "__keep__":
            if style.get("paint-order") != "stroke":
                raise DocumentError("halo_width needs a halo colour.")
            color = style["stroke"]
        width = spec.get("halo_width")
        if width is None:
            fs = parse_length(style.get("font-size"))
            width = round(0.3 * (fs[0] if fs else self._font_size(el)), 4)
        if float(width) <= 0:
            raise DocumentError("halo_width must be > 0.")
        style.update({"paint-order": "stroke", "stroke": str(color), "stroke-width": _num(float(width)),
                      "stroke-linejoin": "round"})

    def _image(self, el: etree._Element, spec: dict[str, Any]) -> None:
        """A linked (file:/// URI) or embedded (data URI) picture. Inkscape resolves neither plain
        Windows paths nor relative ones from our temp copies (E25). Missing width/height come from the
        file's pixel size at 96 dpi, keeping the aspect ratio."""
        import base64

        from . import files

        if "href" in spec:
            href = str(spec["href"])
            if href.startswith(("http:", "https:")):
                raise DocumentError("Images must be local files (no downloads).")
            if href.startswith("data:"):
                el.set(_q("href", XLINK_NS), href)
                el.attrib.pop(SRC_ATTR, None)
            else:
                if href.startswith("file:"):
                    from urllib.parse import unquote, urlparse
                    href = unquote(urlparse(href).path.lstrip("/") if re.match(r"file:///[A-Za-z]:", href)
                                   else urlparse(href).path)
                path = files.resolve(href, self)
                if path.suffix.lower() not in files.IMAGE_TYPES:
                    raise DocumentError(f"{path.name}: not an image type Inkscape renders "
                                        f"({', '.join(sorted(files.IMAGE_TYPES))}).")
                el.set(SRC_ATTR, str(path))
                if spec.get("embed"):
                    data = base64.b64encode(path.read_bytes()).decode()
                    el.set(_q("href", XLINK_NS), f"data:{files.IMAGE_TYPES[path.suffix.lower()]};base64,{data}")
                else:
                    el.set(_q("href", XLINK_NS), path.as_uri())
        elif spec.get("embed") and el.get(SRC_ATTR):
            self._image(el, {"href": el.get(SRC_ATTR), "embed": True})
        if el.get(_q("href", XLINK_NS)) is None:
            raise DocumentError("image needs href (a file path).")
        w, h = el.get("width"), el.get("height")
        if w is None or h is None:
            size = files.image_size(Path(el.get(SRC_ATTR))) if el.get(SRC_ATTR) else None
            if size is None:
                raise DocumentError("Give width and height (the image's pixel size is unknown).")
            pw, ph = size[0] / self.px_per_user_unit, size[1] / self.px_per_user_unit  # 96 dpi
            if w is None and h is None:
                w, h = pw, ph
            elif w is None:
                w = float(h) * pw / ph
            else:
                h = float(w) * ph / pw
            el.set("width", _num(round(float(w), 4)))
            el.set("height", _num(round(float(h), 4)))
        for k in ("x", "y"):
            if el.get(k) is None:
                el.set(k, "0")
        if "object_fit" in spec:
            if spec["object_fit"] not in OBJECT_FIT:
                raise DocumentError(f"object_fit must be one of {sorted(OBJECT_FIT)}.")
            el.set("preserveAspectRatio", OBJECT_FIT[spec["object_fit"]])

    FIT_MODES = ("both", "height", "width")

    def _use(self, el: etree._Element, spec: dict[str, Any]) -> dict[str, str]:
        """href "id" / "#id": an element or symbol in this document; "file.svg#id": that symbol (and what it
        references) is copied into our defs once, then linked. Returns paint the library's root gave its
        symbols (inherited through the use), for keys the spec doesn't set."""
        href = str(spec.get("href") or "")
        ref, _, frag = href.rpartition("#")
        if not frag:
            raise DocumentError('use needs href: "symbol_id" or "library.svg#symbol_id".')
        paint: dict[str, str] = {}
        unit = 1.0  # library user units per ours, so a symbol keeps its physical size
        if ref:
            from . import files  # files imports this module
            frag, paint, lib_px = files.bring_symbol(self, ref, frag)
            unit = lib_px / self.px_per_user_unit
        elif self._find(frag) is None:
            syms = [e.get("id") for e in self.find({"type": "symbol"})][:8]
            raise DocumentError(f"No element {frag!r} to use." + (f" Symbols here include {syms}." if syms else ""))
        el.set(_q("href", XLINK_NS), "#" + frag)
        el.set(USE_ATTR, json.dumps({"unit": unit}))
        return paint

    def _use_size(self, el: etree._Element, spec: dict[str, Any]) -> None:
        """width/height only scale a symbol that has a viewBox (SVG). For anything else the engine measures
        the content and scales it with the transform (`size_uses`); a library symbol without a size keeps its
        physical size. A symbol with a viewBox and no size gets its viewBox size (else it fills the page)."""
        data = json.loads(el.get(USE_ATTR) or "{}")
        target = self._find((el.get(_q("href", XLINK_NS)) or el.get("href") or "").lstrip("#"))
        vb = target.get("viewBox") if target is not None and _local(target) == "symbol" else None
        unit = float(data.get("unit", 1.0))
        if vb:
            if el.get("width") is None and el.get("height") is None:
                _, _, w, h = (float(v) for v in re.split(r"[\s,]+", vb.strip()))
                el.set("width", _num(round(w * unit, 4)))
                el.set("height", _num(round(h * unit, 4)))
            el.set(USE_ATTR, json.dumps({"unit": unit}))
            return
        box = {k: data[k] for k in ("x", "y", "w", "h") if data.get(k) is not None}
        for k, attr in (("x", "x"), ("y", "y"), ("w", "width"), ("h", "height")):
            if attr in spec:
                if spec[attr] is None:
                    box.pop(k, None)
                else:
                    box[k] = float(spec[attr])
            elif el.get(attr) is not None and k not in box:
                box[k] = float(el.get(attr))
            el.attrib.pop(attr, None)  # the engine writes the transform instead
        if "transform" in spec and spec["transform"] and ("w" in box or "h" in box or abs(unit - 1) > 1e-9):
            raise DocumentError("This use is sized through its transform (its symbol has no viewBox): "
                                "give x, y, width, height instead of transform.")
        el.set(USE_ATTR, json.dumps({"unit": unit, **box, "pending": True}))

    def _set_fit(self, el: etree._Element, spec: dict[str, Any]) -> None:
        """Store what a rect fits around; the engine sizes it once the targets are measured."""
        old = json.loads(el.get(FIT_ATTR) or "null")
        if "fit_to" in spec and not spec["fit_to"]:
            el.attrib.pop(FIT_ATTR, None)  # fit_to: null / [] -> size it by hand again
            return
        ids = spec.get("fit_to", (old or {}).get("ids"))
        if not ids:
            raise DocumentError("fit_padding / fit need fit_to (the ids the rect should surround).")
        if isinstance(ids, str):
            ids = [ids]
        pad = spec.get("fit_padding", (old or {}).get("padding", 0))
        pad = [pad] if isinstance(pad, (int, float)) else list(pad)
        if len(pad) not in (1, 2, 4) or not all(isinstance(v, (int, float)) for v in pad):
            raise DocumentError("fit_padding must be a number, [vertical, horizontal] or [top, right, bottom, left].")
        if len(pad) == 1:
            pad = pad * 4
        elif len(pad) == 2:
            pad = [pad[0], pad[1], pad[0], pad[1]]
        mode = spec.get("fit", (old or {}).get("fit", "both"))
        if mode not in self.FIT_MODES:
            raise DocumentError(f"fit must be one of {self.FIT_MODES}.")
        el.set(FIT_ATTR, json.dumps({"ids": list(ids), "padding": pad, "fit": mode}, separators=(",", ":")))

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
    def computed(self, el: etree._Element, prop: str) -> str | None:
        """A property as it renders: the element's style, then its presentation attribute, then its
        ancestors' (inherited). None = the SVG initial value (fill black, stroke none)."""
        e = el
        while e is not None and isinstance(e.tag, str):
            v = parse_style(e.get("style")).get(prop, e.get(prop))
            if v is not None and v != "inherit":
                return v
            e = e.getparent()
        return None

    def describe(self, el: etree._Element, bboxes: dict | None = None) -> dict[str, Any]:
        """One element for the agent: id, type, label, bbox, computed fill/stroke/opacity, text, href."""
        tag = _local(el)
        is_layer = tag == "g" and el.get(_q("groupmode", INKSCAPE_NS)) == "layer"
        d: dict[str, Any] = {"id": el.get("id"), "type": "layer" if is_layer else (
            "group" if tag == "g" else "flowtext" if tag == "flowRoot" else tag)}
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
        if tag not in ("g", "symbol"):
            for k in ("fill", "stroke"):
                v = self.computed(el, k)
                if v is not None:
                    d[k] = v
            if "opacity" in parse_style(el.get("style")) or el.get("opacity") is not None:
                d["opacity"] = parse_style(el.get("style")).get("opacity", el.get("opacity"))
        if tag == "image":
            src = el.get(SRC_ATTR) or el.get(_q("href", XLINK_NS)) or ""
            d["src"] = Path(src).name if el.get(SRC_ATTR) else src[:40]
        if tag == "use":
            d["href"] = (el.get(_q("href", XLINK_NS)) or el.get("href") or "").lstrip("#")
        if tag == "text":
            spans = [c for c in el if _local(c) == "tspan"]
            d["text"] = "\n".join("".join(s.itertext()) for s in spans) if spans else "".join(el.itertext())
        if tag == "flowRoot":
            paras = [c for c in el.iter() if isinstance(c.tag, str) and _local(c) in ("flowPara", "flowDiv")
                     and not any(_local(k) in ("flowPara", "flowDiv") for k in c if isinstance(k.tag, str))]
            text = "\n".join("".join(p.itertext()) for p in paras)
            d["text"] = text if len(text) <= 160 else text[:160] + "..."
            d["note"] = "SVG 1.2 flowed text: move, align, delete and z-order work; its text can't be edited."
        if tag == "symbol":
            title = next((c.text for c in el if isinstance(c.tag, str) and _local(c) == "title"), None)
            if title:
                d["title"] = title
        if el.get("transform"):
            d["transform"] = el.get("transform")
        return d

    def find(self, query: dict[str, Any]) -> list[etree._Element]:
        """Elements matching every key of `query`: type (as inspect names it, e.g. "path", "text",
        "use", "symbol"), fill / stroke (computed, colours compared as #rrggbb), text (substring,
        case-insensitive), href (use target id), id_prefix. Symbols in defs are included for type "symbol"."""
        allowed = {"type", "fill", "stroke", "text", "href", "id_prefix"}
        bad = set(query) - allowed
        if bad:
            raise DocumentError(f"find keys {sorted(bad)} unknown; use {sorted(allowed)}.")
        unseen = ("defs", "clipPath", "mask", "marker", "pattern", "symbol")
        out = []
        for el in self.root.iter():
            if not isinstance(el.tag, str) or not el.get("id"):
                continue
            tag = _local(el)
            if tag != "symbol" and any(_local(a) in unseen for a in el.iterancestors()):
                continue
            if tag not in SHAPE_TAGS and tag != "symbol":
                continue
            if tag == "symbol" and query.get("type") != "symbol":
                continue
            d = self.describe(el)
            if "type" in query and d["type"] != query["type"] and tag != query["type"]:
                continue
            if any(k in query and norm_color(d.get(k)) != norm_color(str(query[k])) for k in ("fill", "stroke")):
                continue
            if "text" in query and str(query["text"]).lower() not in (
                    "".join(el.itertext()) if tag == "flowRoot" else d.get("text", "")).lower():  # N6: all of it
                continue
            if "href" in query and d.get("href") != str(query["href"]).lstrip("#"):
                continue
            if "id_prefix" in query and not el.get("id").startswith(str(query["id_prefix"])):
                continue
            out.append(el)
        return out

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
            d = self.describe(el, bboxes)
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
