"""Inkscape-backed operations on a Document: geometry queries, actions, export, preview.

The Document (lxml) is the source of truth. For each operation we hand Inkscape a
temp copy through the persistent shell, then close it again.
"""
from __future__ import annotations

import copy
import json
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

from . import grids, layout
from .document import (GRID_ATTR, PARA_ATTR, ROUTE_ATTR, SHAPE_TAGS, WRAP_ATTR, Document, DocumentError,
                       _local)
from .inkscape import InkscapeError, InkscapeShell

EXPORT_TYPES = {"png", "pdf", "svg", "plain-svg", "eps", "ps", "emf", "wmf"}

# Export options persist for the whole shell session, even across file-open (E05).
# Every export therefore sets every option explicitly, starting from this baseline.
# The export area is deliberately not here: export-area-page beats export-id, so each
# export picks exactly one area mode itself (E06).
EXPORT_BASELINE = [
    "export-id:",
    "export-id-only:false",
    "export-width:0",
    "export-height:0",
    "export-dpi:96",
    "export-margin:0",
    "export-background-opacity:0",
    "export-plain-svg:false",
    "export-text-to-path:false",
]

# Actions the generic `run_actions` escape hatch must not run: they touch files,
# the export state, the shell itself, or need a GUI.
BLOCKED_ACTION_PREFIXES = ("quit", "file-", "export-", "window-", "dialog-", "app-", "win.", "doc.")


MAX_SHELL_LINE = 15000  # a 16.7k-char line was proven safe (E16b)


def _join_lines(actions: list[str]) -> list[str]:
    lines, cur = [], ""
    for a in actions:
        if cur and len(cur) + 1 + len(a) > MAX_SHELL_LINE:
            lines.append(cur)
            cur = a
        else:
            cur = f"{cur};{a}" if cur else a
    if cur:
        lines.append(cur)
    return lines


def off_page_warnings(doc: Document, boxes: dict[str, tuple[float, float, float, float]],
                      tol: float = 0.01) -> list[str]:
    """The agent rarely notices clipping in a preview; say it explicitly (E10)."""
    px, py, pw, ph = doc.viewbox
    out = []
    for id_, (x, y, w, h) in boxes.items():
        over = []
        if x < px - tol:
            over.append(f"left by {px - x:.2f}")
        if x + w > px + pw + tol:
            over.append(f"right by {x + w - px - pw:.2f}")
        if y < py - tol:
            over.append(f"top by {py - y:.2f}")
        if y + h > py + ph + tol:
            over.append(f"bottom by {y + h - py - ph:.2f}")
        if over:
            out.append(f"{id_!r} extends beyond the page ({', '.join(over)} {doc.unit}).")
    return out


class _Measured:
    """Measured boxes for one align/layout call, kept true as moves accumulate."""

    def __init__(self, doc: Document, boxes: dict, caps: dict):
        self.doc, self.boxes, self.caps = doc, boxes, caps
        self.total: dict[str, tuple[float, float]] = {}

    def eff(self, id_: str) -> layout.Box:
        """Visual bbox, but vertically the cap box for text (so labels share baselines)."""
        if id_ not in self.boxes:
            self.doc.get(id_)
            raise DocumentError(f"{id_!r} has no visible geometry.")
        x, y, w, h = self.boxes[id_]
        if id_ in self.caps:
            _, y, _, h = self.caps[id_]
        return x, y, w, h

    def union(self, ids: list[str]) -> layout.Box:
        return layout.union([self.eff(i) for i in ids])

    def reference(self, to: str, ids: list[str]) -> layout.Box:
        if to == "page":
            return self.doc.viewbox
        if to == "selection":
            return self.union(ids)
        return self.eff(to)

    def move(self, id_: str, dx: float, dy: float) -> None:
        tx, ty = self.total.get(id_, (0.0, 0.0))
        self.total[id_] = (tx + dx, ty + dy)
        for e in self.doc.get(id_).iter():  # descendants move too
            sub = e.get("id") if isinstance(e.tag, str) else None
            for cache in (self.boxes, self.caps):
                if sub in cache:
                    cache[sub] = layout.shift(cache[sub], dx, dy)


class Engine:
    def __init__(self, shell: InkscapeShell | None = None):
        self._shell = shell
        self._tmp = Path(tempfile.mkdtemp(prefix="inksmcp-"))

    @property
    def shell(self) -> InkscapeShell:
        if self._shell is None:
            self._shell = InkscapeShell()
        return self._shell

    def close(self) -> None:
        if self._shell:
            self._shell.close()
        shutil.rmtree(self._tmp, ignore_errors=True)

    # -- helpers ---------------------------------------------------------
    def _tmpfile(self, suffix: str) -> Path:
        return self._tmp / f"{uuid.uuid4().hex[:12]}{suffix}"

    def _open(self, doc: Document) -> Path:
        src = self._tmpfile(".svg")
        src.write_bytes(doc.to_bytes())
        self.shell.run("file-close", check=False)
        self.shell.run(f"file-open:{src}")
        return src

    def _close(self, *files: Path) -> None:
        self.shell.run("file-close", check=False)
        for f in files:
            f.unlink(missing_ok=True)

    # -- queries ---------------------------------------------------------
    def bboxes(self, doc: Document) -> dict[str, tuple[float, float, float, float]]:
        """Visual bounding boxes of every element, in document user units."""
        src = self._open(doc)
        try:
            out = self.shell.run("query-all").output
        finally:
            self._close(src)
        s = doc.px_per_user_unit
        vx, vy = doc.viewbox[:2]
        boxes: dict[str, tuple[float, float, float, float]] = {}
        for line in out.splitlines():
            parts = line.strip().split(",")
            if len(parts) != 5:
                continue
            try:
                x, y, w, h = (float(v) / s for v in parts[1:])
            except ValueError:
                continue
            boxes[parts[0]] = (x + vx, y + vy, w, h)
        return boxes

    def measure(self, doc: Document, cap_ids: list[str] = ()) -> tuple[dict, dict]:
        """Visual bboxes of everything, plus a *cap box* for each text in `cap_ids`.

        The cap box spans from the cap height of the first line to the baseline of the last
        line — measured by rendering a clone whose every line reads "H" (E07: metrics differ
        per font, so they must be measured). Centring by cap box gives labels with identical
        baselines regardless of ascenders/descenders.
        """
        probe = Document.from_bytes(doc.to_bytes(), doc.path)
        probe_ids = {}
        for tid in cap_ids:
            el = probe.get(tid)
            if _local(el) != "text":
                continue
            clone = copy.deepcopy(el)
            pid = f"__cap_{tid}"
            clone.set("id", pid)
            for n, node in enumerate(clone.iterdescendants()):
                if node.get("id"):
                    node.set("id", f"{pid}_{n}")
            for node in clone.iter():
                if node.text and node.text.strip():
                    node.text = "H"
                if node is not clone and node.tail and node.tail.strip():
                    node.tail = None
            el.addnext(clone)
            probe_ids[tid] = pid
        boxes = self.bboxes(probe)
        caps = {tid: boxes.pop(pid) for tid, pid in probe_ids.items() if pid in boxes}
        for k in [k for k in boxes if k.startswith("__cap_")]:
            del boxes[k]
        return boxes, caps

    def translate(self, doc: Document, moves: dict[str, tuple[float, float]]) -> None:
        """Move elements by (dx, dy) user units. Inkscape handles transforms/groups/text;
        its transform-translate takes px, not user units (E07)."""
        s = doc.px_per_user_unit
        # Connectors follow their endpoints; translating one as well moves it twice (E11, F20).
        connectors = {c.get("id") for c in doc.connectors()}
        by_delta: dict[tuple[float, float], list[str]] = {}
        for id_, (dx, dy) in moves.items():
            if id_ in connectors:
                continue
            # moves derive from query-all boxes (~6 significant digits, F19): snap to 0.001 user
            # units so a 35 mm move is written as 35, not 34.999973
            dx, dy = round(dx, 3), round(dy, 3)
            if abs(dx) > 1e-9 or abs(dy) > 1e-9:
                by_delta.setdefault((dx, dy), []).append(id_)
        actions = []
        for (dx, dy), ids in by_delta.items():  # one selection per distinct move: 150x faster (E16b)
            actions += ["select-clear", "select-by-id:" + ",".join(ids),
                        f"transform-translate:{dx * s:.6f},{dy * s:.6f}"]
        if actions:
            self.run_actions(doc, actions)
            doc.tidy_numbers([i for i in moves if i not in connectors])
            self.reroute(doc)  # our own connectors follow (native ones were re-routed on load)

    def align(self, doc: Document, operations: list[dict[str, Any]]) -> dict[str, Any]:
        """Run align operations in order with one measurement and one Inkscape pass.

        Each op: ids, to ('page' | 'selection' | element id), horizontal, vertical,
        as_group, margin, text_metrics ('cap' | 'visual').
        """
        cap_ids = set()
        for i, op in enumerate(operations):
            if not op.get("ids"):
                raise DocumentError(f"operations[{i}]: 'ids' is required.")
            if not op.get("horizontal") and not op.get("vertical"):
                raise DocumentError(f"operations[{i}]: give horizontal and/or vertical.")
            to = op.get("to", "page")
            refs = [to] if to not in ("page", "selection") else []
            if op.get("text_metrics", "cap") == "cap":
                cap_ids |= self._texts(doc, list(op["ids"]) + refs)
            else:
                for id_ in list(op["ids"]) + refs:
                    doc.get(id_)
        m = _Measured(doc, *self.measure(doc, sorted(cap_ids)))
        for op in operations:
            ids, to = list(op["ids"]), op.get("to", "page")
            ref = m.reference(to, ids)
            h, v, margin = op.get("horizontal"), op.get("vertical"), float(op.get("margin") or 0)
            if op.get("as_group"):
                d = layout.align_delta(m.union(ids), ref, h, v, margin)
                for i in ids:
                    m.move(i, *d)
            else:
                for i in ids:
                    m.move(i, *layout.align_delta(m.eff(i), ref, h, v, margin))
        return self._apply(doc, m)

    def layout(self, doc: Document, items: list[str | list[str]], direction: str = "row",
               gap: float | tuple[float, float] = 0.0, columns: int | None = None, align: str = "center",
               at: tuple[float, float] | None = None, to: str | None = None, horizontal: str | None = None,
               vertical: str | None = None, margin: float = 0.0) -> dict[str, Any]:
        """Arrange items in a row, column or grid. An item is an id or a list of ids that move
        together (e.g. a box and its label). The block stays where its first item was, or goes
        to `at` (top-left), or is aligned to `to` ('page' or an id) with horizontal/vertical."""
        if not items:
            raise DocumentError("layout needs at least one item.")
        groups = [[i] if isinstance(i, str) else list(i) for i in items]
        if any(not g for g in groups):
            raise DocumentError("layout items must not be empty.")
        all_ids = [i for g in groups for i in g]
        if len(set(all_ids)) != len(all_ids):
            raise DocumentError("An id appears in more than one layout item.")
        refs = [to] if to and to not in ("page", "selection") else []
        m = _Measured(doc, *self.measure(doc, sorted(self._texts(doc, all_ids + refs))))
        boxes = [m.union(g) for g in groups]
        try:
            offsets, (bw, bh) = layout.arrange([(b[2], b[3]) for b in boxes], direction, gap, columns, align)
        except ValueError as e:
            raise DocumentError(str(e)) from e
        if at is not None:
            ox, oy = at
        else:
            ox, oy = boxes[0][0] - offsets[0][0], boxes[0][1] - offsets[0][1]
        if to:
            if not horizontal and not vertical:
                raise DocumentError("With 'to', give horizontal and/or vertical.")
            dx, dy = layout.align_delta((ox, oy, bw, bh), m.reference(to, all_ids), horizontal, vertical, margin)
            ox, oy = ox + (dx if horizontal else 0), oy + (dy if vertical else 0)
        for g, b, (px, py) in zip(groups, boxes, offsets):
            for i in g:
                m.move(i, ox + px - b[0], oy + py - b[1])
        result = self._apply(doc, m)
        result["block"] = [round(v, 2) for v in (ox, oy, bw, bh)]
        return result

    def connect(self, doc: Document, specs: list[dict[str, Any]]) -> dict[str, Any]:
        """Add native connectors, let Inkscape route them, then place their labels."""
        ids, warnings = [], []
        try:
            for i, spec in enumerate(specs):
                try:
                    cid, w = doc.add_connector(spec)
                except DocumentError as e:
                    raise DocumentError(f"connections[{i}]: {e}") from e
                ids.append(cid)
                warnings += w
        except DocumentError:
            for cid in ids:
                doc.delete(cid)
            raise
        self.sync(doc)
        return {"ids": ids, "warnings": warnings}

    def grid(self, doc: Document, rect: list[float], x: dict[str, Any] | None, y: dict[str, Any] | None,
             color: str = "#7f7f7f", weights: dict[str, float] | None = None, border: float | None = None,
             labels: dict[str, Any] | None = None, layer_prefix: str = "Grid", id_prefix: str = "grid") -> dict:
        """Graph-paper style grid inside `rect`: one path per weight class (minor/medium/major, each in
        its own layer, finest at the bottom), an optional border, and optional edge labels.
        Axes: {"scale": "linear", "major", "medium", "minor", "label_start", "label_step"} or
        {"scale": "log", "cycles", "subdivisions"}; "reverse": true flips the direction
        (default x left→right, y bottom→top)."""
        if len(rect) != 4 or rect[2] <= 0 or rect[3] <= 0:
            raise DocumentError("rect must be [x, y, width, height] with positive size.")
        if not x and not y:
            raise DocumentError("Give an x and/or y axis.")
        rx, ry, rw, rh = (float(v) for v in rect)
        mm = (96 / 25.4) / doc.px_per_user_unit  # user units per mm
        w = {"major": 0.45 * mm, "medium": 0.22 * mm, "minor": 0.08 * mm}
        unknown = set(weights or {}) - set(w)
        if unknown:
            raise DocumentError(f"weights keys must be major/medium/minor, not {sorted(unknown)}")
        w.update(weights or {})
        border = 0.6 * mm if border is None else border

        def ticks(spec, length):
            if not spec:
                return []
            spec = dict(spec)
            rev = bool(spec.pop("reverse", False))
            try:
                t = grids.axis_ticks(spec, length)
            except ValueError as e:
                raise DocumentError(str(e)) from e
            return [((length - p) if rev else p, c, lab) for p, c, lab in t]

        xt = ticks(x, rw)  # offsets from the left
        yt = [(rh - p, c, lab) for p, c, lab in ticks(y, rh)]  # y grows upwards by default
        segs: dict[str, list[str]] = {c: [] for c in grids.CLASSES}
        on_edge = lambda p, length: border and (p < 1e-6 or abs(p - length) < 1e-6)  # noqa: E731
        for p, c, _ in xt:
            if not on_edge(p, rw):
                segs[c].append(f"M {rx + p:.4f},{ry:.4f} V {ry + rh:.4f}")
        for p, c, _ in yt:
            if not on_edge(p, rh):
                segs[c].append(f"M {rx:.4f},{ry + p:.4f} H {rx + rw:.4f}")
        ids: dict[str, Any] = {}
        for c in grids.CLASSES:
            if segs[c]:
                ids[c] = doc.add({"type": "path", "id": doc.free_id(f"{id_prefix}-{c}"), "d": " ".join(segs[c]),
                                  "fill": "none", "stroke": color, "stroke_width": w[c],
                                  "layer": f"{layer_prefix} {c}"})
        if border:
            ids["border"] = doc.add({"type": "rect", "id": doc.free_id(f"{id_prefix}-border"), "x": rx, "y": ry,
                                     "width": rw, "height": rh, "fill": "none", "stroke": color,
                                     "stroke_width": border, "layer": f"{layer_prefix} major"})
        # remember the axes so `plot` can map data values onto this grid
        meta = json.dumps({"prefix": id_prefix, "layer_prefix": layer_prefix, "rect": [rx, ry, rw, rh],
                           "x": x, "y": y}, separators=(",", ":"))
        for i in ids.values():
            doc.get(i).set(GRID_ATTR, meta)
        n_labels = 0
        if labels:
            n_labels = self._grid_labels(doc, labels, xt, yt, (rx, ry, rw, rh), color, mm, layer_prefix, id_prefix)
        return {"ids": ids, "lines": {c: len(segs[c]) for c in grids.CLASSES}, "labels": n_labels}

    def plot(self, doc: Document, grid: str, series: list[dict[str, Any]]) -> dict[str, Any]:
        """Draw data series on a grid made by `grid`, in data values: a line and/or point markers,
        optional point labels. Uses the grid's own value→position mapping (field report 2)."""
        meta = next((json.loads(e.get(GRID_ATTR)) for e in doc.root.iter()
                     if isinstance(e.tag, str) and e.get(GRID_ATTR) and json.loads(e.get(GRID_ATTR))["prefix"] == grid),
                    None)
        if meta is None:
            raise DocumentError(f"No grid with id_prefix {grid!r}. Create one with the grid tool first.")
        rx, ry, rw, rh = meta["rect"]

        def mapper(spec, length):
            if not spec:
                raise DocumentError("This grid has no axis for that direction.")
            f = grids.axis_mapper(spec, length)
            rev = bool(spec.get("reverse"))
            return (lambda v: length - f(v)) if rev else f

        fx, fy = mapper(meta["x"], rw), mapper(meta["y"], rh)
        allowed = {"id", "points", "line", "stroke", "stroke_width", "stroke_dasharray", "marker", "marker_size",
                   "marker_fill", "point_labels", "label_font_size", "label_offset", "label_color", "font_family",
                   "layer"}
        mm = (96 / 25.4) / doc.px_per_user_unit
        out: dict[str, Any] = {"series": [], "warnings": []}
        anchors = {}
        for n, s in enumerate(series):
            unknown = set(s) - allowed
            if unknown:
                raise DocumentError(f"series[{n}]: unknown keys {sorted(unknown)}; allowed {sorted(allowed)}")
            pts_data = s.get("points") or []
            if not pts_data or any(len(p) != 2 for p in pts_data):
                raise DocumentError(f"series[{n}]: points must be [[x, y], ...].")
            try:
                pts = [(rx + fx(float(px)), ry + rh - fy(float(py))) for px, py in pts_data]
            except ValueError as e:
                raise DocumentError(f"series[{n}]: {e}") from e
            for (px, py), (ux, uy) in zip(pts_data, pts):
                if not (rx - 1e-6 <= ux <= rx + rw + 1e-6 and ry - 1e-6 <= uy <= ry + rh + 1e-6):
                    out["warnings"].append(f"series[{n}] point [{px}, {py}] lies outside the grid.")
            color = s.get("stroke", "#1f77b4")
            layer = s.get("layer", f"{meta['layer_prefix']} data")
            gid = doc.add({"type": "group", "id": s.get("id") or doc.free_id(f"{grid}-series"), "layer": layer})
            ids = {"group": gid}
            if s.get("line", True) and len(pts) > 1:
                ids["line"] = doc.add({"type": "polyline", "parent": gid, "points": [list(p) for p in pts],
                                       "stroke": color, "stroke_width": s.get("stroke_width", 0.5 * mm),
                                       "stroke_linejoin": "round", "fill": "none",
                                       **({"stroke_dasharray": s["stroke_dasharray"]}
                                          if s.get("stroke_dasharray") else {})})
            marker = s.get("marker", "circle")
            size = float(s.get("marker_size", 1.6 * mm))
            fill = s.get("marker_fill", "#ffffff")
            ids["markers"] = []
            for ux, uy in pts:
                if marker == "circle":
                    spec = {"type": "circle", "cx": ux, "cy": uy, "r": size / 2}
                elif marker == "square":
                    spec = {"type": "rect", "x": ux - size / 2, "y": uy - size / 2, "width": size, "height": size}
                elif marker == "diamond":
                    h = size / 2 * 1.3
                    spec = {"type": "polygon", "points": [[ux, uy - h], [ux + h, uy], [ux, uy + h], [ux - h, uy]]}
                elif marker == "none":
                    continue
                else:
                    raise DocumentError("marker must be circle/square/diamond/none.")
                ids["markers"].append(doc.add({**spec, "parent": gid, "fill": fill, "stroke": color,
                                               "stroke_width": s.get("stroke_width", 0.5 * mm) * 0.8}))
            labels = s.get("point_labels") or []
            if labels:
                if len(labels) != len(pts):
                    raise DocumentError(f"series[{n}]: point_labels needs one entry (or null) per point.")
                lfs = float(s.get("label_font_size", 2.4 * mm))
                ids["labels"] = []
                for k, ((ux, uy), text) in enumerate(zip(pts, labels)):
                    if not text:
                        continue
                    if "label_offset" in s:
                        dx, dy = s["label_offset"]
                    else:  # right of the point, on the side the line is NOT heading to (E18)
                        prev, nxt = pts[max(0, k - 1)], pts[min(len(pts) - 1, k + 1)]
                        rising = nxt[1] - prev[1] < 0  # user y grows downwards
                        dx, dy = size * 1.2, (size * 1.5 if rising else -size * 1.5)
                    tid = doc.add({"type": "text", "parent": gid, "x": ux + dx, "y": uy + dy, "text": str(text),
                                   "font_size": lfs, "fill": s.get("label_color", color),
                                   "text_anchor": "start" if dx >= 0 else "end",
                                   # white halo keeps the label readable where the series line crosses it
                                   "style": {"paint-order": "stroke", "stroke": "#ffffff",
                                             "stroke-width": f"{lfs * 0.3:.4f}", "stroke-linejoin": "round"},
                                   **({"font_family": s["font_family"]} if s.get("font_family") else {})})
                    anchors[tid] = ("middle", uy + dy)
                    ids["labels"].append(tid)
            ids["points"] = [[round(x, 3), round(y, 3)] for x, y in pts]
            out["series"].append(ids)
        if anchors:
            self.anchor_texts(doc, anchors)
        if not out["warnings"]:
            del out["warnings"]
        return out

    def _grid_labels(self, doc, labels, xt, yt, rect, color, mm, layer_prefix, id_prefix) -> int:
        allowed = {"sides", "font_size", "gap", "color", "font_family", "bold_major", "x_title", "y_title",
                   "title_font_size"}
        unknown = set(labels) - allowed
        if unknown:
            raise DocumentError(f"labels keys must be in {sorted(allowed)}, not {sorted(unknown)}")
        rx, ry, rw, rh = rect
        sides = labels.get("sides", ["left", "bottom"])
        fs = float(labels.get("font_size", 2.2 * mm))
        gap = float(labels.get("gap", 1.2 * mm))
        base = {"type": "text", "font_size": fs, "fill": labels.get("color", color),
                "font_family": labels.get("font_family", "sans-serif"), "layer": f"{layer_prefix} labels"}
        specs = []
        for side in sides:
            if side in ("left", "right"):
                for p, c, lab in yt:
                    if lab is None:
                        continue
                    specs.append(dict(base, text=lab, y=ry + p, vertical_anchor="middle",
                                      x=rx - gap if side == "left" else rx + rw + gap,
                                      text_anchor="end" if side == "left" else "start", _major=c == "major"))
            elif side in ("top", "bottom"):
                for p, c, lab in xt:
                    if lab is None:
                        continue
                    specs.append(dict(base, text=lab, x=rx + p, text_anchor="middle",
                                      y=ry + rh + gap if side == "bottom" else ry - gap,
                                      vertical_anchor="top" if side == "bottom" else "bottom", _major=c == "major"))
            else:
                raise DocumentError(f"label side must be left/right/top/bottom, not {side!r}")
        anchors = {}
        for s in specs:
            major = s.pop("_major")
            if major and labels.get("bold_major", True):
                s["font_weight"] = "bold"
            anchor = s.pop("vertical_anchor")
            s["id"] = doc.free_id(f"{id_prefix}-label")
            tid = doc.add(s)
            anchors[tid] = (anchor, s["y"])
        if anchors:
            self.anchor_texts(doc, anchors)
        titles = [k for k in ("x_title", "y_title") if labels.get(k)]
        if titles:
            # place titles clear of the measured tick labels
            boxes = self.bboxes(doc)
            placed = [boxes[t] for t in anchors if t in boxes]
            below = max([b[1] + b[3] for b in placed if b[1] > ry + rh] + [ry + rh])
            left = min([b[0] for b in placed if b[0] + b[2] < rx] + [rx])
            tfs = float(labels.get("title_font_size", fs * 1.25))
            common = dict(base, font_size=tfs, text_anchor="middle")
            if labels.get("x_title"):
                tid = doc.add(dict(common, id=doc.free_id(f"{id_prefix}-x-title"), text=labels["x_title"],
                                   x=rx + rw / 2, y=below + gap * 1.5))
                self.anchor_texts(doc, {tid: ("top", below + gap * 1.5)})
            if labels.get("y_title"):
                x = left - gap * 1.5 - 0.24 * tfs  # rotated: glyphs extend from the baseline towards -x
                cy = ry + rh / 2
                doc.add(dict(common, id=doc.free_id(f"{id_prefix}-y-title"), text=labels["y_title"], x=x, y=cy,
                             transform=f"rotate(-90 {x:.4f} {cy:.4f})"))
        return len(specs) + len(titles)

    def wrap_texts(self, doc: Document, ids: list[str]) -> dict[str, int]:
        """Break texts that carry a wrap width into lines no wider than it. Word widths are
        measured by Inkscape on probe clones (same parent, style and font) in one pass; lines are
        then filled greedily. Explicit newlines stay paragraph breaks. Returns lines per id."""
        targets = [i for i in ids if doc.get(i).get(WRAP_ATTR)]
        if not targets:
            return {}
        probe = Document.from_bytes(doc.to_bytes(), doc.path)
        words: dict[str, dict[str, str]] = {}
        n = 0

        def add_probe(tid: str, s: str) -> str:
            nonlocal n
            src = probe.get(tid)
            clone = copy.deepcopy(src)
            for c in list(clone):
                clone.remove(c)
            clone.text = s
            n += 1
            clone.set("id", f"__w{n}")
            for a in (WRAP_ATTR, PARA_ATTR):
                clone.attrib.pop(a, None)
            src.addnext(clone)
            return clone.get("id")

        for tid in targets:
            text = doc.text_of(doc.get(tid))
            vocab = {w for para in text.split("\n") for w in para.split()}
            words[tid] = {w: add_probe(tid, w) for w in vocab}
            words[tid]["\0xx"] = add_probe(tid, "xx")
            words[tid]["\0x x"] = add_probe(tid, "x x")
        boxes = self.bboxes(probe)
        result = {}
        for tid in targets:
            el = doc.get(tid)
            width = float(el.get(WRAP_ATTR))
            w = {k: boxes.get(v, (0, 0, 0, 0))[2] for k, v in words[tid].items()}
            space = max(0.0, w["\0x x"] - w["\0xx"])
            source = doc.text_of(el)
            lines: list[str] = []
            for para in source.split("\n"):
                cur, cur_w = [], 0.0
                for word in para.split():
                    add = w[word] + (space if cur else 0)
                    if cur and cur_w + add > width:
                        lines.append(" ".join(cur))
                        cur, cur_w = [word], w[word]
                    else:
                        cur.append(word)
                        cur_w += add
                lines.append(" ".join(cur))
            doc.set_wrapped(el, source, lines)
            result[tid] = len(lines)
        return result

    def anchor_texts(self, doc: Document, anchors: dict[str, tuple[str, float]]) -> None:
        """Move texts so `y` marks their cap top / cap middle / last baseline instead of the first
        baseline. Measured per font with cap-box probes (E07), so no guessed offsets."""
        _, caps = self.measure(doc, list(anchors))
        moves = {}
        for id_, (mode, y) in anchors.items():
            if id_ not in caps:
                continue
            _, top, _, h = caps[id_]
            now = {"top": top, "middle": top + h / 2, "bottom": top + h}[mode]
            moves[id_] = (0.0, y - now)
        self.translate(doc, moves)

    def page_fit(self, doc: Document, margin: float | list[float] = 0.0,
                 ids: list[str] | None = None) -> dict[str, Any]:
        """Shrink/grow the page to the drawing (or `ids`) plus margin. Content is moved so the page
        origin stays 0,0 (Inkscape's own page-fit also moves content, but has no margin and leaves
        backgrounds behind — E11). margin: one number, [vertical, horizontal] or [top, right, bottom, left]."""
        m = [margin] if isinstance(margin, (int, float)) else list(margin)
        if len(m) not in (1, 2, 4) or any(v < 0 for v in m):
            raise DocumentError("margin must be >= 0: one number, [vertical, horizontal] or [top, right, bottom, left].")
        top, right, bottom, left = (m * 4)[:4] if len(m) == 1 else (m * 2 if len(m) == 2 else m)
        backgrounds = set(doc.page_backgrounds())
        top_level = [c.get("id") for c in doc.root if _local(c) in SHAPE_TAGS and c.get("id") not in backgrounds]
        boxes = self.bboxes(doc)
        targets = ids or top_level
        for i in targets:
            doc.get(i)
        present = [boxes[i] for i in targets if i in boxes and boxes[i][2] + boxes[i][3] > 0]
        if not present:
            raise DocumentError("Nothing visible to fit the page to.")
        x0, y0, w, h = layout.union(present)
        dx, dy = left - x0, top - y0
        # query-all has ~6 significant digits (F19): 100 mm measures as 99.9999
        doc.set_page_size(round(w + left + right, 3), round(h + top + bottom, 3))
        # everything moves together (not only `ids`) so the drawing keeps its composition
        self.translate(doc, {i: (dx, dy) for i in top_level})
        _, _, pw, ph = doc.viewbox
        return {"page": {"width": pw, "height": ph, "unit": doc.unit}, "content_moved_by": [round(dx, 3), round(dy, 3)],
                "backgrounds_resized": sorted(backgrounds)}

    def z_order(self, doc: Document, ids: list[str], op: str, target: str | None = None) -> dict[str, Any]:
        """Stacking order. front/back/above/below are exact (lxml). forward/backward use Inkscape's
        raise/lower, which step past the next *overlapping* object — a visible change (E13)."""
        if not ids:
            raise DocumentError("z_order needs ids.")
        before = {i: doc.stack_position(i) for i in ids}
        notes = []
        if op in ("forward", "backward"):
            action = "selection-raise" if op == "forward" else "selection-lower"
            actions = []
            for i in ids:  # one at a time: multi-selection raise is unpredictable (E13)
                actions += ["select-clear", f"select-by-id:{i}", action]
            self.run_actions(doc, actions)
        else:
            doc.z_order(ids, op, target)
            self.sync(doc)
        after = {i: doc.stack_position(i) for i in ids}
        for i in ids:
            if op in ("forward", "backward") and after[i]["index"] == before[i]["index"]:
                notes.append(f"{i!r} unchanged: nothing it overlaps is {'above' if op == 'forward' else 'below'} it.")
        result: dict[str, Any] = {"positions": after}
        if notes:
            result["notes"] = notes
        return result

    def move_to(self, doc: Document, ids: list[str], container: str, position: str = "top") -> dict[str, Any]:
        dest = doc.move_to(ids, container, position)
        self.sync(doc)
        return {"container": dest.get("id"), "positions": {i: doc.stack_position(i) for i in ids}}

    def sync(self, doc: Document) -> None:
        """Bring every connector route (and label) up to date with the geometry: Inkscape re-routes
        native connectors on load; ours (sides/via) are recomputed from measured boxes."""
        if doc.connectors("native"):
            self.run_actions(doc, [])
        if doc.connectors("routed"):
            self.reroute(doc)

    def reroute(self, doc: Document, boxes: dict | None = None) -> None:
        """Recompute connectors that carry a route spec (from_side/to_side/via)."""
        routed = doc.connectors("routed")
        if not routed:
            return
        boxes = boxes or self.bboxes(doc)
        stub = 3 * (96 / 25.4) / doc.px_per_user_unit  # leave/enter a shape straight for 3 mm
        for el in routed:
            r = json.loads(el.get(ROUTE_ATTR))
            a, b = boxes.get(r["from"]), boxes.get(r["to"])
            if a is None or b is None:
                continue
            pts = layout.route(a, b, r.get("from_side") if r.get("from_side") != "auto" else None,
                               r.get("to_side") if r.get("to_side") != "auto" else None,
                               r.get("via"), r.get("routing", "straight"), stub)
            # routes are in document coordinates; the path lives in its parent's coordinates.
            # Snap to 0.001: endpoints come from query-all boxes (~6 significant digits, F19).
            inv = layout.mat_inv(doc._ctm(el.getparent()))
            local = [(round(inv[0] * x + inv[2] * y + inv[4], 3), round(inv[1] * x + inv[3] * y + inv[5], 3))
                     for x, y in pts]
            el.set("d", layout.polyline_d(local))
            el.attrib.pop("transform", None)
        doc.place_connector_labels()

    # -- helpers for align/layout ----------------------------------------
    @staticmethod
    def _texts(doc: Document, ids: list[str]) -> set[str]:
        return {i for i in ids if _local(doc.get(i)) == "text"}

    def _apply(self, doc: Document, m: "_Measured") -> dict[str, Any]:
        self.translate(doc, m.total)  # the Inkscape round-trip also re-routes connectors
        moved = {k: [round(v[0], 3), round(v[1], 3)] for k, v in m.total.items() if abs(v[0]) + abs(v[1]) > 1e-9}
        result: dict[str, Any] = {
            "moved": moved, "bboxes": {k: [round(c, 2) for c in m.boxes[k]] for k in m.total if k in m.boxes}}
        warnings = off_page_warnings(doc, {k: m.boxes[k] for k in m.total if k in m.boxes})
        if warnings:
            result["warnings"] = warnings
        return result

    # -- actions ---------------------------------------------------------
    def run_actions(self, doc: Document, actions: list[str], select: list[str] | None = None,
                    guard: bool = True) -> list[str]:
        """Run Inkscape actions on the document and load the result back into `doc`."""
        for a in actions:
            if ";" in a or "\n" in a:
                raise InkscapeError(f"Action must not contain ';' or newlines: {a!r}")
            if guard and a.split(":", 1)[0].strip().startswith(BLOCKED_ACTION_PREFIXES):
                raise InkscapeError(f"Action {a!r} is not allowed here.")
        for id_ in select or []:
            doc.get(id_)  # clear error before touching Inkscape
        src = self._open(doc)
        dst = self._tmpfile(".svg")
        messages: list[str] = []
        try:
            if select:
                messages += self.shell.run("select-clear;select-by-id:" + ",".join(select)).messages
            for line in _join_lines(actions):  # one shell round-trip per ~15k chars (E16b: 9x faster)
                messages += self.shell.run(line).messages
            self.shell.run(";".join(EXPORT_BASELINE + ["export-area-page", f"export-filename:{dst}",
                                                       "export-type:svg", "export-do"]))
            new = Document.from_bytes(dst.read_bytes(), doc.path)
        finally:
            self._close(src, dst)
        doc.root = new.root
        doc.ensure_ids()
        if doc.connectors():  # Inkscape re-routed connectors on load; labels follow
            doc.place_connector_labels()
        return messages

    # -- export ----------------------------------------------------------
    def _area_px(self, doc: Document, box: layout.Box) -> str:
        """export-area takes px (96 dpi) relative to the viewBox origin, not user units (E15)."""
        vx, vy = doc.viewbox[:2]
        s = doc.px_per_user_unit
        x, y, w, h = box
        return f"export-area:{(x - vx) * s:.4f}:{(y - vy) * s:.4f}:{(x + w - vx) * s:.4f}:{(y + h - vy) * s:.4f}"

    @staticmethod
    def _isolated(doc: Document, ids: list[str]) -> Document:
        """Copy of `doc` where everything except `ids` (their ancestors and descendants) is hidden."""
        copy_ = Document.from_bytes(doc.to_bytes(), doc.path)
        keep = {copy_.get(i) for i in ids}
        ancestors = {a for e in keep for a in e.iterancestors()}

        def visit(el) -> None:
            for child in el:
                if not isinstance(child.tag, str) or _local(child) not in SHAPE_TAGS or child in keep:
                    continue
                if child in ancestors:
                    visit(child)
                else:
                    style = child.get("style", "")
                    child.set("style", (style + ";" if style else "") + "display:none")

        visit(copy_.root)
        return copy_

    def export(self, doc: Document, target: str | Path | None, fmt: str | None = None, *,
               area: str = "page", ids: list[str] | None = None, only_ids: bool = True,
               region: tuple[float, float, float, float] | None = None, dpi: float | None = None,
               width: int | None = None, height: int | None = None, background: str | None = None,
               margin: float = 0, text_to_path: bool = False) -> Path:
        """Export to a file.

        region [x, y, w, h] (user units): that rectangle, everything visible.
        ids + only_ids: just those objects, cropped to them. ids without only_ids: the area of
        their union with everything visible (a zoom). Otherwise `area` = 'page' | 'drawing'.
        """
        target = Path(target) if target else self._tmpfile(f".{fmt or 'png'}")
        fmt = (fmt or target.suffix.lstrip(".") or "png").lower()
        if fmt not in EXPORT_TYPES:
            raise InkscapeError(f"Unsupported export type {fmt!r}; use one of {sorted(EXPORT_TYPES)}")
        for id_ in ids or []:
            doc.get(id_)
        work, box = doc, None
        if region is not None:
            if len(region) != 4 or region[2] <= 0 or region[3] <= 0:
                raise DocumentError("region must be [x, y, width, height] with positive size.")
            box = tuple(region)
        elif ids and not (only_ids and len(ids) == 1):
            boxes = self.bboxes(doc)
            missing = [i for i in ids if i not in boxes]
            if missing:
                raise DocumentError(f"No visible geometry for {missing}.")
            box = layout.union([boxes[i] for i in ids])
            if only_ids:  # export-id takes exactly one id (E15): hide the rest instead
                work = self._isolated(doc, ids)
        ext = "svg" if fmt == "plain-svg" else fmt
        tmp_out = self._tmpfile(f".{ext}")
        opts = list(EXPORT_BASELINE)
        if box is not None:
            opts.append(self._area_px(doc, box))
        elif ids:
            opts += [f"export-id:{ids[0]}", "export-id-only:true", "export-area-drawing"]
        elif area == "drawing":
            opts.append("export-area-drawing")
        elif area == "page":
            opts.append("export-area-page")
        else:
            raise InkscapeError("area must be 'page' or 'drawing' (or pass ids / region).")
        if dpi:
            opts.append(f"export-dpi:{dpi}")
        if width:
            opts.append(f"export-width:{int(width)}")
        if height:
            opts.append(f"export-height:{int(height)}")
        if background:
            opts += [f"export-background:{background}", "export-background-opacity:1"]
        if margin:
            opts.append(f"export-margin:{margin}")
        if text_to_path:
            opts.append("export-text-to-path:true")
        if fmt == "plain-svg":
            opts.append("export-plain-svg:true")
        opts += [f"export-type:{ext}", f"export-filename:{tmp_out}", "export-do"]
        src = self._open(work)
        try:
            self.shell.run(";".join(opts))
            if not tmp_out.exists():
                raise InkscapeError(f"Inkscape did not produce {fmt} output.")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(tmp_out), target)
        finally:
            self._close(src, tmp_out)
        return target

    def render_png(self, doc: Document, max_size: int = 800, area: str = "page",
                   ids: list[str] | None = None, region: tuple[float, float, float, float] | None = None,
                   only_ids: bool = False, background: str = "#ffffff") -> bytes:
        """PNG preview whose longest side is `max_size` px. `ids`/`region` zoom in with everything
        visible, unless only_ids (field report 2026-09-27: agents expect a zoom)."""
        if region is None and ids and not only_ids:
            boxes = self.bboxes(doc)
            missing = [i for i in ids if i not in boxes]
            if missing:
                raise DocumentError(f"No visible geometry for {missing}.")
            region = layout.union([boxes[i] for i in ids])
            ids = None
        if region is not None:
            w, h = region[2], region[3]
        elif ids:
            boxes = self.bboxes(doc)
            b = layout.union([boxes[i] for i in ids if i in boxes] or [(0, 0, 1, 1)])
            w, h = b[2], b[3]
        elif area == "drawing":
            b = self.bboxes(doc).get(doc.root.get("id"), (0, 0, 1, 1))
            w, h = b[2], b[3]
        else:
            _, _, w, h = doc.viewbox
        size = {"width": max_size} if w >= h else {"height": max_size}
        out = self.export(doc, None, "png", area=area, ids=ids, only_ids=True, region=region,
                          background=background, **size)
        try:
            return out.read_bytes()
        finally:
            out.unlink(missing_ok=True)
