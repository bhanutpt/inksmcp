"""MCP layer: thin tool wrappers over Document (lxml) and Engine (Inkscape)."""
from __future__ import annotations

import atexit
import functools
import json
from pathlib import Path
from typing import Any, Literal

from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, Field

from . import __version__
from .document import GEOMETRY, STYLE_KEYS, Document, DocumentError
from .engine import Engine
from .inkscape import InkscapeError, find_inkscape, inkscape_version

INSTRUCTIONS = """Drive Inkscape to create and edit SVG documents.
Workflow: document_create/document_open -> add_elements (batch!) -> render_preview to check -> export/document_save.
All coordinates are in the document's user units (the unit given at creation; viewBox origin top-left, y down).
Tools default to the current document, so doc_id is rarely needed.
Use inspect to get ids and real bounding boxes (text included) before positioning things relative to each other.
Prefer relationships over coordinates: layout arranges rows/columns/grids, align centres labels in boxes
(labels then share baselines), connect draws arrows that stay attached. Drop new elements anywhere, then arrange.
Pass preview=true to editing tools to get a rendered image back in the same call."""

mcp = MCPServer("inksmcp", instructions=INSTRUCTIONS, version=__version__)


def tool(**kwargs):
    """Register a tool whose expected failures reach the agent with their message.

    MCP 2.x replaces the text of any non-ToolError exception with a generic
    "Error executing tool X", which leaves the agent unable to recover.
    """

    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            try:
                return fn(*a, **kw)
            except (DocumentError, InkscapeError, OSError) as e:
                raise ToolError(str(e)) from e

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
    "Element spec keys â€” common: type, id, label, layer (name; created if missing), parent (group id), "
    "transform, style (css string or dict). Style shorthands: " + ", ".join(STYLE_KEYS) + ". Geometry per type: "
    + "; ".join(f"{k}: {', '.join(v) or '-'}" for k, v in GEOMETRY.items())
    + ". points = [[x,y],...]. text supports '\\n' for multiple lines; font_size is in user units."
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
def inspect(doc_id: str | None = None, bbox: bool = True) -> str:
    """Outline of the document: layers, groups and elements with ids, fill/stroke, text and
    real visual bounding boxes [x, y, width, height] in user units (measured by Inkscape)."""
    doc_id, doc = session.get(doc_id)
    boxes = session.engine.bboxes(doc) if bbox else None
    return _j({"doc_id": doc_id, "page": _page(doc), "outline": doc.outline(boxes)})


@tool(description="Add one or more elements in a single call. Returns the new ids.\n" + ELEMENT_HELP)
def add_elements(elements: list[dict[str, Any]], doc_id: str | None = None, preview: bool = False):
    doc_id, doc = session.get(doc_id)
    ids = []
    for i, spec in enumerate(elements):
        try:
            ids.append(doc.add(spec))
        except DocumentError as e:
            for done in ids:  # all-or-nothing
                doc.delete(done)
            raise DocumentError(f"elements[{i}]: {e}") from e
    return _with_preview({"doc_id": doc_id, "ids": ids}, doc, preview)


@tool()
def update_elements(updates: list[dict[str, Any]], doc_id: str | None = None, preview: bool = False):
    """Change existing elements. Each update is {"id": ..., <any element-spec keys>}; only the given
    keys change. Style shorthands merge into the existing style. Set transform to "" to clear it."""
    doc_id, doc = session.get(doc_id)
    for i, u in enumerate(updates):
        u = dict(u)
        if "id" not in u:
            raise DocumentError(f"updates[{i}] needs an 'id'.")
        target = u.pop("id")
        if "new_id" in u:
            u["id"] = u.pop("new_id")
        doc.update(target, u)
    session.engine.sync(doc)  # connectors follow moved shapes
    return _with_preview({"doc_id": doc_id, "updated": len(updates)}, doc, preview)


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
    label: str | None = Field(None, description="Text centred on the connector's midpoint, with a white halo.")
    font_size: float | None = None
    layer: str | None = None


@tool()
def connect(connections: list[Connection], doc_id: str | None = None, preview: bool = False):
    """Draw arrows/lines between elements. They are native Inkscape connectors: they attach to the
    shapes' edges (clipped to circles etc.) and stay attached when things move — here via align/layout/
    update_elements, and later in the Inkscape GUI. Returns the connector ids and any warnings."""
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
    and text into paths. The result keeps the bottom object's id and style."""
    doc_id, doc = session.get(doc_id)
    before = set(doc.ids())
    messages = session.engine.run_actions(doc, [PATH_OPS[operation]], select=ids)
    after = doc.ids()
    return _with_preview({
        "doc_id": doc_id,
        "removed": sorted(before - set(after)),
        "created": [i for i in after if i not in before],
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


class AlignOp(BaseModel):
    ids: list[str] = Field(description="Elements to move.")
    to: str = Field("page", description="Reference: 'page', 'selection' (bbox of all ids), or an element id.")
    horizontal: Literal["left", "center", "right"] | None = None
    vertical: Literal["top", "middle", "bottom"] | None = None
    as_group: bool = Field(False, description="Move all ids together, keeping their relative positions.")
    margin: float = Field(0, description="Inset from the reference edge in user units (ignored for center/middle).")
    text_metrics: Literal["cap", "visual"] = Field(
        "cap", description="For text: 'cap' aligns vertically by cap-height..baseline so labels share baselines "
                           "(default); 'visual' uses the glyph bbox.")


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
           area: Literal["page", "drawing"] = "page", ids: list[str] | None = None, dpi: float | None = None,
           width: int | None = None, height: int | None = None, background: str | None = None,
           text_to_path: bool = False, doc_id: str | None = None) -> str:
    """Export the document (or only `ids`) via Inkscape. Format defaults to the file extension.
    For PNG set dpi or width/height (px); background e.g. '#ffffff' (default transparent)."""
    doc_id, doc = session.get(doc_id)
    out = session.engine.export(doc, Path(path).expanduser(), format, area=area, ids=ids, dpi=dpi, width=width,
                                height=height, background=background, text_to_path=text_to_path)
    return _j({"doc_id": doc_id, "exported": str(out), "bytes": out.stat().st_size})


@tool()
def render_preview(max_size: int = 800, area: Literal["page", "drawing"] = "page", ids: list[str] | None = None,
                   doc_id: str | None = None):
    """Render the document (or only `ids`) to a PNG image you can look at, on a white background."""
    _, doc = session.get(doc_id)
    return Image(data=session.engine.render_png(doc, max_size=max_size, area=area, ids=ids), format="png")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
