"""MCP layer: thin tool wrappers over Document (lxml) and Engine (Inkscape)."""
from __future__ import annotations

import atexit
import copy
import functools
import json
import re
from pathlib import Path
from typing import Any, Literal

from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, Field

from . import __version__, files, templates
from .document import GEOMETRY, SHAPE_TAGS, STYLE_KEYS, WRAP_ATTR, Document, DocumentError, _local
from .engine import Engine, off_page_warnings
from .inkscape import InkscapeError, find_inkscape, inkscape_version

INSTRUCTIONS = """Drive Inkscape to create and edit SVG documents.
Workflow: document_create/document_open -> add_elements (batch!) -> render_preview to check -> export/document_save.
All coordinates are in the document's user units (the unit given at creation; viewBox origin top-left, y down).
Tools default to the current document, so doc_id is rarely needed.
Use inspect to get ids and real bounding boxes (text included) before positioning things relative to each other.
Prefer relationships over coordinates: layout arranges rows/columns/grids, align centres labels in boxes
(labels then share baselines), connect draws arrows that stay attached, repeat stamps one block per data row
(timelines, card grids, legends). Drop new elements anywhere, then arrange.
Pass preview=true to editing tools to get a rendered image back in the same call."""

mcp = MCPServer("inksmcp", instructions=INSTRUCTIONS, version=__version__)


def tool(**kwargs):
    """Register a tool whose expected failures reach the agent with their message.

    MCP 2.x replaces the text of any non-ToolError exception with a generic
    "Error executing tool X", which leaves the agent unable to recover.

    Every tool is all-or-nothing: a failure part-way (e.g. the Inkscape shell dying after the
    elements were written but before wrapping/fitting ran, field report 5) restores the document.
    """

    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            doc = session.docs.get(kw.get("doc_id") or session.current)
            saved = (copy.deepcopy(doc.root), doc.path) if doc is not None else None
            try:
                return fn(*a, **kw)
            except Exception as e:
                if saved is not None:
                    doc.root, doc.path = saved
                if isinstance(e, (DocumentError, InkscapeError, OSError)):
                    raise ToolError(str(e) + (" (Nothing was changed.)" if saved is not None else "")) from e
                raise

        return mcp.tool(structured_output=False, **kwargs)(wrapper)

    return deco


class Session:
    def __init__(self) -> None:
        self.docs: dict[str, Document] = {}
        self.current: str | None = None
        self._n = 0
        self._engine: Engine | None = None

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = Engine()
            atexit.register(self._engine.close)
        return self._engine

    def add(self, doc: Document) -> str:
        self._n += 1
        doc_id = f"doc{self._n}"
        self.docs[doc_id] = doc
        self.current = doc_id
        return doc_id

    def get(self, doc_id: str | None) -> tuple[str, Document]:
        doc_id = doc_id or self.current
        if not doc_id:
            raise DocumentError("No document open. Call document_create or document_open first.")
        if doc_id not in self.docs:
            raise DocumentError(f"Unknown doc_id {doc_id!r}; open: {sorted(self.docs)}")
        self.current = doc_id
        return doc_id, self.docs[doc_id]


session = Session()


def _j(obj: Any) -> str:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def _page(doc: Document) -> dict[str, Any]:
    _, _, w, h = doc.viewbox
    return {"width": w, "height": h, "unit": doc.unit, "path": str(doc.path) if doc.path else None}


def _with_preview(result: dict[str, Any], doc: Document, preview: bool, max_size: int = 800) -> str | list:
    if not preview:
        return _j(result)
    return [_j(result), Image(data=session.engine.render_png(doc, max_size=max_size), format="png")]


ELEMENT_HELP = (
    "Element spec keys — common: type, id, label, layer (name; created if missing), parent (group id), "
    "transform, style (css string or dict). Style shorthands: " + ", ".join(STYLE_KEYS) + ". Geometry per type: "
    + "; ".join(f"{k}: {', '.join(v) or '-'}" for k, v in GEOMETRY.items())
    + ". points = [[x,y],...]. text supports '\\n' for multiple lines; font_size is in user units."
    + " Coordinates are in the parent's system: inside a transformed layer or group (e.g. after layout moved"
      " it, or a scaled plan group) they are offset/scaled with it."
    + " clip: an element id (its current shape) or [x, y, w, h] — the element is cut to it and the clip then"
      " moves with the element; null removes it. text halo: '#ffffff' outlines the glyphs behind the fill so"
      " text reads over lines (halo_width default 0.3 x font size; 'none' removes)."
    + " rect fit_to: [ids] sizes the rect around them after wrapping (fit_padding: n | [v, h] | [t, r, b, l];"
      " fit: both | height | width, e.g. height keeps a card's width); it re-fits when those elements are"
      " edited (update_elements {\"id\": rect} re-fits after moves; fit_to: null frees it)."
)


@tool()
def inkscape_info() -> str:
    """Inkscape version and location, server version, and open documents."""
    exe = find_inkscape()
    return _j({
        "inkscape": inkscape_version(exe),
        "path": str(exe),
        "server_version": __version__,
        "current": session.current,
        "documents": {k: _page(d) for k, d in session.docs.items()},
    })


@tool()
def document_create(width: float, height: float, unit: Literal["px", "mm", "cm", "in", "pt"] = "px",
                    background: str | None = None) -> str:
    """Create a new blank document and make it current. The viewBox matches width/height,
    so coordinates are in `unit`. `background` (e.g. '#ffffff') adds a full-page rect with id 'background'."""
    doc = Document.create(width, height, unit, background)
    doc_id = session.add(doc)
    return _j({"doc_id": doc_id, "page": _page(doc)})


@tool()
def document_open(path: str) -> str:
    """Open an existing SVG file and make it current. Returns its outline."""
    doc = Document.open(Path(path).expanduser())
    doc_id = session.add(doc)
    return _j({"doc_id": doc_id, "page": _page(doc), "outline": doc.outline()})


@tool()
def document_save(path: str | None = None, doc_id: str | None = None) -> str:
    """Save the document as Inkscape SVG (to `path`, or where it was opened/last saved)."""
    doc_id, doc = session.get(doc_id)
    saved = doc.save(Path(path).expanduser() if path else None)
    return _j({"doc_id": doc_id, "saved": str(saved)})


@tool()
def inspect(doc_id: str | None = None, bbox: bool = True, layer: str | None = None,
            max_children: int = 40) -> str:
    """Outline of the document: layers, groups and elements with ids, fill/stroke, text and
    real visual bounding boxes [x, y, width, height] in user units (measured by Inkscape).
    Layers/groups with more than `max_children` children are summarised (counts per type, first/last
    ids, bbox). To list one of them, pass `layer` (layer name or group id) and a larger max_children."""
    doc_id, doc = session.get(doc_id)
    root = None
    if layer:
        found = doc._find(layer)
        root = found if found is not None and found.tag.endswith("}g") else doc.layer(layer, create=False)
    boxes = session.engine.bboxes(doc) if bbox else None
    result = {"doc_id": doc_id, "page": _page(doc)}
    if root is not None:
        result["layer"] = root.get("id")
    result["outline"] = doc.outline(boxes, max_children=max_children, root=root)
    return _j(result)


@tool(description="Add one or more elements in a single call. Returns the new ids.\n" + ELEMENT_HELP
      + "\n`defaults` is merged into every element (only keys valid for its type), e.g. "
        "{\"font_size\": 2.2, \"fill\": \"#2a8a4a\", \"layer\": \"Labels\"}."
        "\nelements_path: a JSON file (a list of specs, or {\"elements\": [...], \"defaults\": {...}}) instead of "
        "`elements` — for generated geometry, so it never passes through the conversation.")
def add_elements(elements: list[dict[str, Any]] | None = None, defaults: dict[str, Any] | None = None,
                 elements_path: str | None = None, doc_id: str | None = None, preview: bool = False):
    doc_id, doc = session.get(doc_id)
    source = None
    if elements_path:
        if elements:
            raise DocumentError("Give elements or elements_path, not both.")
        source = files.resolve(elements_path, doc)
        elements, file_defaults = files.read_specs(source)
        defaults = {**file_defaults, **(defaults or {})}
    if not elements:
        raise DocumentError("Give elements (a list of specs) or elements_path.")
    defaults = defaults or {}
    types = {e.get("type") for e in elements}
    unused = [k for k in defaults if not any(doc.accepts(t, k) for t in types)]
    if unused:
        raise DocumentError(f"defaults keys {unused} are not valid for any element type in this batch.")
    ids, anchors = [], {}
    for i, spec in enumerate(elements):
        spec = {**{k: v for k, v in defaults.items() if doc.accepts(spec.get("type"), k)}, **spec}
        try:
            ids.append(doc.add(spec))
        except DocumentError as e:
            for done in ids:  # all-or-nothing
                doc.delete(done)
            raise DocumentError(f"elements[{i}]: {e}") from e
    result = {"doc_id": doc_id, "ids": templates.compact(ids) if source else ids}
    if source:
        result["source"] = {"path": str(source), "elements": len(ids)}
    result.update(_text_post(doc, list(zip(ids, (dict(defaults, **e) for e in elements)))))
    return _with_preview(result, doc, preview)


@tool()
def repeat(template: list[dict[str, Any]], step: list[float], rows: list[dict[str, Any]] | None = None,
           rows_path: str | None = None,
           columns: int | None = None, mirror: dict[str, Any] | None = None,
           defaults: dict[str, Any] | None = None, id_prefix: str = "row", layer: str | None = None,
           order: Literal["row", "column"] = "row", doc_id: str | None = None, preview: bool = False):
    """Stamp a block of elements once per data row — timelines, card grids, tables, legends, map
    symbols — in one call.
    template: element specs as for add_elements, drawn for the FIRST row. "{key}" in any string is
    replaced from the row ("{year}"; a value that is exactly "{w}" keeps the row's number), in geometry
    and style alike ("fill": "{colour}"); "{n}" is the row number (1-based) and "{i}" the index, so
    rows can't use the keys n and i. Ids are local names: "card" becomes card-1, card-2, ... A
    "parent" may name another template element (e.g. a group holding a card and its texts); fit_to
    and clip may name template elements of the same row.
    Each row goes into a group <id_prefix>-<n> moved by n-1 steps: step [dx, dy], or a grid with
    `columns` (step = [column pitch, row pitch]), filled row by row or, with order "column", column
    by column. Components (a character, a node, a symbol placed at data positions): a template group
    with "transform": "translate({x},{y}) scale({s})" and step [0, 0], parts drawn around a local
    origin, pose/shape parts as placeholders ("d": "{arms}").
    mirror {"x": 148.5, "rows": "even"|"odd"|"all"} (or "y") mirrors those rows about the axis:
    shapes are reflected (pointers flip), texts and groups keep their reading direction and move as
    blocks — group a card with its texts so they cross together. Per element "mirror":
    "reflect"|"block"|"none" overrides. rows_path: a .json (list of row objects) or .csv file (header
    line = keys, numbers parsed) instead of `rows`, so data never passes through the conversation.
    Returns the row groups, ids per template name (runs shortened to "card-1..card-12"), wrapped_lines, fitted."""
    doc_id, doc = session.get(doc_id)
    if rows_path:
        if rows:
            raise DocumentError("Give rows or rows_path, not both.")
        rows = files.read_rows(files.resolve(rows_path, doc))
    if not rows:
        raise DocumentError("Give rows (a list of objects) or rows_path.")
    defaults = defaults or {}
    template = [{**{k: v for k, v in defaults.items() if doc.accepts(e.get("type"), k)}, **e} for e in template]
    result, touched, blocks = session.engine.stamp_rows(doc, template, rows, step, columns, mirror, id_prefix, layer,
                                                        order)
    try:
        result.update(_text_post(doc, touched))
        session.engine.mirror_blocks(doc, blocks, mirror)
    except Exception:
        for g in result["groups"]:
            doc.delete(g)
        raise
    boxes = session.engine.bboxes(doc)
    warnings = off_page_warnings(doc, {g: boxes[g] for g in result["groups"] if g in boxes})
    if warnings:
        result["warnings"] = warnings
    result["groups"] = templates.compact(result["groups"])
    result["ids"] = {k: templates.compact(v) for k, v in result["ids"].items()}
    return _with_preview({"doc_id": doc_id, **result}, doc, preview)


WRAP_TRIGGERS = {"text", "width", "font_size", "font_family", "font_weight", "font_style", "style"}


def _text_post(doc: Document, touched: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    """Wrap (width), anchor (vertical_anchor) texts, then size fit_to rects around the result —
    all need Inkscape to measure."""
    wrap = [i for i, spec in touched if WRAP_TRIGGERS & set(spec) and doc.get(i).get(WRAP_ATTR)]
    out: dict[str, Any] = {}
    if wrap:
        out["wrapped_lines"] = session.engine.wrap_texts(doc, wrap)
    anchors = {}
    for i, spec in touched:
        mode = spec.get("vertical_anchor", "baseline")
        if mode != "baseline":
            y = spec.get("y", doc.get(i).get("y", 0))
            anchors[i] = (mode, float(y))
    if anchors:
        session.engine.anchor_texts(doc, anchors)
    fitted = session.engine.fit_rects(doc, {i for i, _ in touched})
    if fitted:
        out["fitted"] = fitted
    return out


@tool()
def import_file(path: str, at: list[float] | None = None, width: float | None = None, height: float | None = None,
                layer: str | None = None, parent: str | None = None, id: str | None = None,
                embed: bool = False, object_fit: Literal["contain", "cover", "fill"] | None = None,
                doc_id: str | None = None, preview: bool = False):
    """Place a file into the current document. An SVG (e.g. geometry a script generated) becomes one
    group scaled to this document's units, its top-left at `at` (default 0,0); width or height scales it
    (both: stretch). Its layers become labelled groups, its defs join ours, clashing ids get "<id>-" in front.
    An image (png/jpg/gif/webp/bmp) becomes an image element: natural size at 96 dpi unless width/height
    (one keeps the ratio), linked by default (embed: true stores the pixels in the SVG), object_fit
    contain|cover|fill for a given box. Relative paths start at the document's folder.
    For whole documents use document_open; for data rows see repeat rows_path."""
    doc_id, doc = session.get(doc_id)
    src = files.resolve(path, doc)
    x, y = (at or [0, 0])[:2]
    if src.suffix.lower() == ".svg":
        if embed or object_fit:
            raise DocumentError("embed / object_fit are for images; an SVG is copied in as elements.")
        container = doc.get(parent) if parent else doc.layer(layer) if layer else doc.root
        gid = id or doc.free_id(re.sub(r"[^A-Za-z0-9_-]", "_", src.stem) or "import")
        result = files.import_svg(doc, src, (float(x), float(y)), width, height, container, gid)
    else:
        spec = {"type": "image", "href": str(src), "x": x, "y": y, "embed": embed,
                **{k: v for k, v in (("width", width), ("height", height), ("layer", layer), ("parent", parent),
                                     ("id", id), ("object_fit", object_fit)) if v is not None}}
        iid = doc.add(spec)
        el = doc.get(iid)
        result = {"id": iid, "size": [float(el.get("width")), float(el.get("height"))]}
    boxes = session.engine.bboxes(doc)
    if result["id"] in boxes:
        result["bbox"] = [round(v, 2) for v in boxes[result["id"]]]
        warnings = off_page_warnings(doc, {result["id"]: boxes[result["id"]]})
        if warnings:
            result["warnings"] = warnings
    return _with_preview({"doc_id": doc_id, **result}, doc, preview)


@tool()
def update_elements(updates: list[dict[str, Any]], doc_id: str | None = None, preview: bool = False):
    """Change existing elements. Each update is {"id": ..., <any element-spec keys>}; only the given
    keys change. Style shorthands merge into the existing style. Set transform to "" to clear it."""
    doc_id, doc = session.get(doc_id)
    touched = []
    for i, u in enumerate(updates):
        u = dict(u)
        if "id" not in u:
            raise DocumentError(f"updates[{i}] needs an 'id'.")
        target = u.pop("id")
        if "new_id" in u:
            u["id"] = u.pop("new_id")
        doc.update(target, u)
        touched.append((u.get("id") or target, u))
    result = {"doc_id": doc_id, "updated": len(updates)}
    result.update(_text_post(doc, touched))
    session.engine.sync(doc)  # connectors follow moved shapes
    return _with_preview(result, doc, preview)


@tool()
def delete_elements(ids: list[str], doc_id: str | None = None) -> str:
    """Delete elements (and their children) by id. Connectors attached to them and their labels
    are deleted too; all removed ids are returned."""
    doc_id, doc = session.get(doc_id)
    for id_ in ids:
        doc.get(id_)
    removed: list[str] = []
    for id_ in ids:
        if id_ not in removed:
            removed += doc.delete(id_)
    return _j({"doc_id": doc_id, "deleted": removed})


class Connection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    from_: str = Field(alias="from", description="Start element id (a shape; text routes from its centre).")
    to: str = Field(description="End element id.")
    id: str | None = None
    routing: Literal["straight", "elbow"] = Field("straight", description="elbow = orthogonal segments.")
    arrow: Literal["end", "start", "both", "none"] = "end"
    stroke: str = "#000000"
    stroke_width: float | None = Field(None, description="Default ≈1.5 px in user units.")
    stroke_dasharray: str | None = Field(None, description="e.g. '4 2' for dashed.")
    from_side: Literal["top", "right", "bottom", "left", "auto"] | None = Field(
        None, description="Leave `from` through this side (then the route is computed by inksmcp, not Inkscape).")
    to_side: Literal["top", "right", "bottom", "left", "auto"] | None = Field(
        None, description="Enter `to` through this side.")
    via: list[list[float]] | None = Field(
        None, description="Waypoints [[x, y], ...] the line passes through (corners of a loop, detours).")
    label: str | None = Field(None, description="Text placed on the route (default: middle of the longest segment).")
    label_position: float | None = Field(None, description="0..1 along the route instead of the longest segment.")
    label_offset: float | None = Field(
        None, description="Distance of the label from the line (user units). 0 = on the line with a halo.")
    label_side: Literal["auto", "above", "below", "left", "right"] | None = Field(
        None, description="Where an offset label goes; auto = above horizontal segments, right of vertical ones.")
    label_halo: str | None = Field(None, description="Halo colour behind an on-line label, or 'none' (default white).")
    label_color: str | None = None
    font_size: float | None = None
    font_family: str | None = None
    font_weight: str | None = None
    start_gap: float | None = Field(None, description="Leave this much space before the line starts (user units).")
    end_gap: float | None = Field(None, description="Stop this far short of `to` (e.g. so an arrowhead doesn't touch text).")
    layer: str | None = Field(None, description="Default: the layer both ends are in, else a 'Connectors' layer.")


@tool()
def connect(connections: list[Connection], doc_id: str | None = None, preview: bool = False):
    """Draw arrows/lines between elements that stay attached when things move (align/layout/
    update_elements/page_fit). Default: native Inkscape connectors — clipped to the real shape (circles
    etc.) and still live in the Inkscape GUI. With from_side/to_side/via you control the route (e.g. a
    loop diagram: {"from": "condenser", "to": "valve", "from_side": "left", "to_side": "top",
    "routing": "elbow"}); those attach at the middle of the chosen side of the bounding box, as do
    connectors with start_gap/end_gap. Returns the connector ids, their layers, label ids and warnings."""
    doc_id, doc = session.get(doc_id)
    specs = [{k: v for k, v in c.model_dump(by_alias=True).items() if v is not None} for c in connections]
    result = session.engine.connect(doc, specs)
    return _with_preview({"doc_id": doc_id, **result}, doc, preview)


@tool()
def layout(items: list[str | list[str]], direction: Literal["row", "column", "grid"] = "row",
           gap: float | list[float] = 0, columns: int | None = None,
           align: Literal["start", "center", "end"] = "center", at: list[float] | None = None,
           to: str | None = None, horizontal: Literal["left", "center", "right"] | None = None,
           vertical: Literal["top", "middle", "bottom"] | None = None, margin: float = 0,
           doc_id: str | None = None, preview: bool = False):
    """Arrange items in a row, column or grid with a gap — no coordinate maths needed.
    An item is an id or a list of ids that move together, e.g. ["box1", "box1_label"].
    `gap` is a number or [horizontal, vertical]. `align` places items on the cross axis (grid: within cells).
    The block stays where the first item is, or its top-left goes to `at` [x, y], or it is aligned to
    `to` ('page' or an element id) using horizontal/vertical/margin. Connectors follow."""
    doc_id, doc = session.get(doc_id)
    g = tuple(gap) if isinstance(gap, list) else gap
    if isinstance(g, tuple) and len(g) != 2:
        raise DocumentError("gap must be a number or [horizontal, vertical].")
    result = session.engine.layout(doc, items, direction, g, columns, align, tuple(at) if at else None,
                                   to, horizontal, vertical, margin)
    return _with_preview({"doc_id": doc_id, **result}, doc, preview)


PATH_OPS = {
    "union": "path-union", "difference": "path-difference", "intersection": "path-intersection",
    "exclusion": "path-exclusion", "division": "path-division", "cut": "path-cut",
    "combine": "path-combine", "break_apart": "path-break-apart", "to_path": "object-to-path",
    "stroke_to_path": "object-stroke-to-path", "simplify": "path-simplify", "flatten": "path-flatten",
}


@tool()
def path_operation(operation: Literal["union", "difference", "intersection", "exclusion", "division", "cut",
                                      "combine", "break_apart", "to_path", "stroke_to_path", "simplify", "flatten"],
                   ids: list[str], doc_id: str | None = None, preview: bool = False):
    """Geometry operations performed by Inkscape on the given ids. For difference, the top-most
    (later in document order) object is subtracted from the bottom one. to_path converts shapes
    and text into paths. union/intersection/exclusion/difference keep the BOTTOM object's id, style
    and layer; combine keeps the TOP object's (E22). `result` lists the ids that hold the outcome."""
    doc_id, doc = session.get(doc_id)
    before = set(doc.ids())
    messages = session.engine.run_actions(doc, [PATH_OPS[operation]], select=ids)
    after = doc.ids()
    created = [i for i in after if i not in before]
    return _with_preview({
        "doc_id": doc_id,
        "result": [i for i in ids if i in after] + created,
        "removed": sorted(before - set(after)),
        "created": created,
        "messages": messages,
    }, doc, preview)


@tool()
def run_actions(actions: list[str], select: list[str] | None = None, doc_id: str | None = None,
                preview: bool = False):
    """Escape hatch: run raw Inkscape actions (e.g. "object-align:left last", "transform-rotate:30")
    after selecting `select` ids. File, export, window and quit actions are blocked."""
    doc_id, doc = session.get(doc_id)
    messages = session.engine.run_actions(doc, actions, select=select)
    return _with_preview({"doc_id": doc_id, "messages": messages}, doc, preview)


@tool()
def page_fit(margin: float | list[float] = 0, ids: list[str] | None = None, doc_id: str | None = None,
             preview: bool = False):
    """Resize the page to fit the drawing (or only `ids`) plus `margin` (one number, [vertical, horizontal]
    or [top, right, bottom, left], user units). All content moves together so the page keeps its 0,0
    top-left; full-page background rects are resized, connectors follow."""
    doc_id, doc = session.get(doc_id)
    result = session.engine.page_fit(doc, margin, ids)
    return _with_preview({"doc_id": doc_id, **result}, doc, preview)


@tool()
def page_resize(width: float, height: float,
                anchor: Literal["top-left", "center", "none"] = "top-left", doc_id: str | None = None,
                preview: bool = False):
    """Set the page size in user units (e.g. 210 x 297 for A4 in a mm document). anchor='center' keeps the
    drawing centred on the new page; 'top-left'/'none' leave content where it is. Backgrounds are resized."""
    doc_id, doc = session.get(doc_id)
    _, _, old_w, old_h = doc.viewbox
    backgrounds = doc.set_page_size(width, height)
    top_level = [c.get("id") for c in doc.root
                 if _local(c) in SHAPE_TAGS and c.get("id") and c.get("id") not in backgrounds]
    if anchor == "center":
        dx, dy = (width - old_w) / 2, (height - old_h) / 2
        session.engine.translate(doc, {i: (dx, dy) for i in top_level})
    result = {"doc_id": doc_id, "page": _page(doc), "backgrounds_resized": backgrounds}
    boxes = session.engine.bboxes(doc)
    warnings = off_page_warnings(doc, {i: boxes[i] for i in top_level if i in boxes})
    if warnings:
        result["warnings"] = warnings
    return _with_preview(result, doc, preview)


@tool()
def grid(rect: list[float], x: dict[str, Any] | None = None, y: dict[str, Any] | None = None,
         color: str = "#7f7f7f", weights: dict[str, float] | None = None, border: float | None = None,
         labels: dict[str, Any] | None = None, layer_prefix: str = "Grid", id_prefix: str = "grid",
         doc_id: str | None = None, preview: bool = False):
    """Draw a grid / graph paper inside rect [x, y, w, h] — linear or logarithmic per axis — without
    computing any line positions. Axis specs:
      linear: {"scale": "linear", "major": 10, "medium": 5, "minor": 1, "label_start": 0, "label_step": 1}
              (spacings in user units, each a whole multiple of the finest; labels on major lines)
      log:    {"scale": "log", "cycles": 3, "subdivisions": "standard" | "fine" | "integers", "start": 10}
              (decades major, 2..9 medium, subdivisions minor; "start" = value at the origin (default 1);
              "labels": "decades" (start, start*10, ...; default when start is given) | "paper" (1..9 per cycle))
      "reverse": true flips an axis (default x left→right, y bottom→top); "lines": false keeps the axis
      (labels, `plot` mapping) but draws none of its gridlines, e.g. vertical-only lines for a bar chart.
    weights: {"major", "medium", "minor"} stroke widths (defaults 0.45/0.22/0.08 mm); border: stroke width
    of the frame (default 0.6 mm, 0 = none). labels: {"sides": ["left", "bottom"], "font_size", "gap",
    "color", "font_family", "bold_major", "x_title", "y_title", "title_font_size"} — placed outside the
    grid, centred on their lines (measured); major labels are bold unless "bold_major": false; titles go
    below / left (rotated) of the tick labels.
    Result: one path per weight class in layers '<layer_prefix> minor/medium/major', labels in
    '<layer_prefix> labels'. Use `plot` with grid=<id_prefix> to draw data on it."""
    doc_id, doc = session.get(doc_id)
    result = session.engine.grid(doc, rect, x, y, color, weights, border, labels, layer_prefix, id_prefix)
    return _with_preview({"doc_id": doc_id, **result}, doc, preview)


@tool()
def plot(series: list[dict[str, Any]], grid: str = "grid", doc_id: str | None = None, preview: bool = False):
    """Plot data on a grid made with the `grid` tool, in DATA values — no coordinate maths.
    grid: that grid's id_prefix. Each series: {"points": [[x, y], ...], "line": true, "stroke": "#1f77b4",
    "stroke_width", "stroke_dasharray", "marker": "circle"|"square"|"diamond"|"none", "marker_size",
    "marker_fill" (default white), "point_labels": ["", "COP 3.2", ...] (one per point, null/"" to skip),
    "label_offset": [dx, dy], "label_anchor": "start"|"middle"|"end", "label_halo": "#ffffff"|"none",
    "label_font_size", "label_color", "font_family", "id", "layer"}.
    Labels: label_offset is from the point to the label's anchor, and the label is vertically CENTRED on
    point + dy (dy = 0 → centred on the point). Anchor defaults to start for dx >= 0, else end. Without
    label_offset the label goes right of the point, on the side the line is not heading to. Labels carry a
    halo stroke (default white) so the line can cross them — set label_halo "none" (or the background
    colour) for labels on dark fills; recolouring a label later does not remove its halo (use stroke: "none").
    Ids follow the series id: <id>-line, <id>-marker-<k>, <id>-label-<k> (k = 1-based point index).
    Returns per series those ids and the points in user units (for annotations); warns about points
    outside the grid."""
    doc_id, doc = session.get(doc_id)
    result = session.engine.plot(doc, grid, series)
    return _with_preview({"doc_id": doc_id, **result}, doc, preview)


@tool()
def z_order(ids: list[str], operation: Literal["front", "back", "forward", "backward", "above", "below"],
            target: str | None = None, doc_id: str | None = None, preview: bool = False):
    """Change stacking order (what is drawn on top). front/back: top/bottom within the element's own
    layer or group. forward/backward: one step past the next object it overlaps (visible change).
    above/below: directly above/below `target`, moving into target's layer/group if needed while keeping
    the visual position. Several ids keep their relative order. Returns each id's position."""
    doc_id, doc = session.get(doc_id)
    if operation in ("above", "below") and not target:
        raise DocumentError(f"'{operation}' needs a target id.")
    result = session.engine.z_order(doc, ids, operation, target)
    return _with_preview({"doc_id": doc_id, **result}, doc, preview)


@tool()
def move_to_layer(ids: list[str], layer: str, position: Literal["top", "bottom"] = "top",
                  doc_id: str | None = None, preview: bool = False):
    """Move elements into a layer (by name; created on top if missing) or into a group/layer by id,
    at its top or bottom. They keep their relative order and stay visually where they were."""
    doc_id, doc = session.get(doc_id)
    result = session.engine.move_to(doc, ids, layer, position)
    return _with_preview({"doc_id": doc_id, **result}, doc, preview)


class AlignOp(BaseModel):
    ids: list[str] = Field(description="Elements to move.")
    to: str = Field("page", description="Reference: 'page', 'selection' (bbox of all ids), or an element id.")
    horizontal: Literal["left", "center", "right"] | None = None
    vertical: Literal["top", "middle", "bottom"] | None = None
    as_group: bool = Field(False, description="Move all ids together, keeping their relative positions.")
    margin: float = Field(0, description="Inset from the reference edge in user units (ignored for center/middle).")
    text_metrics: Literal["cap", "visual"] = Field(
        "cap", description="For text: 'cap' aligns vertically by cap-height..baseline so one-line Latin labels "
                           "share baselines (default); 'visual' uses the glyph bbox — better for paragraphs and "
                           "scripts without Latin capitals (Tamil, Devanagari, CJK).")


@tool()
def align(operations: list[AlignOp], doc_id: str | None = None, preview: bool = False):
    """Align elements to the page, to each other, or inside another element — e.g. centre a label in a box:
    {"ids": ["label"], "to": "box", "horizontal": "center", "vertical": "middle"}. Operations run in order,
    each seeing the previous moves. Returns the moves [dx, dy] and new bboxes in user units."""
    doc_id, doc = session.get(doc_id)
    result = session.engine.align(doc, [op.model_dump() for op in operations])
    return _with_preview({"doc_id": doc_id, **result}, doc, preview)


@tool()
def export(path: str, format: Literal["png", "pdf", "svg", "plain-svg", "eps", "ps", "emf", "wmf"] | None = None,
           area: Literal["page", "drawing"] = "page", ids: list[str] | None = None, only_ids: bool = True,
           region: list[float] | None = None, dpi: float | None = None,
           width: int | None = None, height: int | None = None, background: str | None = None,
           text_to_path: bool = False, doc_id: str | None = None) -> str:
    """Export via Inkscape. Format defaults to the file extension. What is exported:
    `region` [x, y, w, h] (user units, everything visible); or `ids` — only those objects cropped to
    them (only_ids=true, default) or the area around them with everything visible (only_ids=false);
    otherwise area 'page' or 'drawing'. For PNG set dpi or width/height (px); background e.g. '#ffffff'
    (default transparent)."""
    doc_id, doc = session.get(doc_id)
    out = session.engine.export(doc, Path(path).expanduser(), format, area=area, ids=ids, only_ids=only_ids,
                                region=tuple(region) if region else None, dpi=dpi, width=width,
                                height=height, background=background, text_to_path=text_to_path)
    return _j({"doc_id": doc_id, "exported": str(out), "bytes": out.stat().st_size})


@tool()
def render_preview(max_size: int = 800, area: Literal["page", "drawing"] = "page", ids: list[str] | None = None,
                   region: list[float] | None = None, only_ids: bool = False, doc_id: str | None = None):
    """Render to a PNG image you can look at (white background, longest side = max_size px).
    Zoom in with `region` [x, y, w, h] in user units, or with `ids` (the area around them, everything
    still visible). only_ids=true draws just those objects."""
    _, doc = session.get(doc_id)
    return Image(data=session.engine.render_png(doc, max_size=max_size, area=area, ids=ids,
                                                region=tuple(region) if region else None, only_ids=only_ids),
                 format="png")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
