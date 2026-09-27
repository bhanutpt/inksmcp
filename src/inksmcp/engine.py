"""Inkscape-backed operations on a Document: geometry queries, actions, export, preview.

The Document (lxml) is the source of truth. For each operation we hand Inkscape a
temp copy through the persistent shell, then close it again.
"""
from __future__ import annotations

import copy
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

from . import layout
from .document import Document, DocumentError, _local
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
        actions = []
        for id_, (dx, dy) in moves.items():
            if abs(dx) > 1e-9 or abs(dy) > 1e-9:
                actions += ["select-clear", f"select-by-id:{id_}", f"transform-translate:{dx * s:.6f},{dy * s:.6f}"]
        if actions:
            self.run_actions(doc, actions)

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

    def sync(self, doc: Document) -> None:
        """Round-trip through Inkscape so connector routes (and their labels) match the geometry."""
        if doc.connectors():
            self.run_actions(doc, [])

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
            for a in actions:
                messages += self.shell.run(a).messages
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
    def export(self, doc: Document, target: str | Path | None, fmt: str | None = None, *,
               area: str = "page", ids: list[str] | None = None, dpi: float | None = None,
               width: int | None = None, height: int | None = None, background: str | None = None,
               margin: float = 0, text_to_path: bool = False) -> Path:
        """Export to a file. `area` is 'page', 'drawing', or ignored when `ids` is given."""
        target = Path(target) if target else self._tmpfile(f".{fmt or 'png'}")
        fmt = (fmt or target.suffix.lstrip(".") or "png").lower()
        if fmt not in EXPORT_TYPES:
            raise InkscapeError(f"Unsupported export type {fmt!r}; use one of {sorted(EXPORT_TYPES)}")
        for id_ in ids or []:
            doc.get(id_)
        ext = "svg" if fmt == "plain-svg" else fmt
        tmp_out = self._tmpfile(f".{ext}")
        opts = list(EXPORT_BASELINE)
        if ids:
            opts += [f"export-id:{','.join(ids)}", "export-id-only:true", "export-area-drawing"]
        elif area == "drawing":
            opts.append("export-area-drawing")
        elif area == "page":
            opts.append("export-area-page")
        else:
            raise InkscapeError("area must be 'page' or 'drawing' (or pass ids).")
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
        src = self._open(doc)
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
                   ids: list[str] | None = None, background: str = "#ffffff") -> bytes:
        """PNG preview whose longest side is `max_size` px."""
        if ids:
            boxes = self.bboxes(doc)
            xs = [boxes[i] for i in ids if i in boxes]
            w = max(b[0] + b[2] for b in xs) - min(b[0] for b in xs) if xs else 1
            h = max(b[1] + b[3] for b in xs) - min(b[1] for b in xs) if xs else 1
        elif area == "drawing":
            b = self.bboxes(doc).get(doc.root.get("id"), (0, 0, 1, 1))
            w, h = b[2], b[3]
        else:
            _, _, w, h = doc.viewbox
        size = {"width": max_size} if w >= h else {"height": max_size}
        out = self.export(doc, None, "png", area=area, ids=ids, background=background, **size)
        try:
            return out.read_bytes()
        finally:
            out.unlink(missing_ok=True)
