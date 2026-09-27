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
            for id_ in list(op["ids"]) + ([to] if to not in ("page", "selection") else []):
                el = doc.get(id_)
                if op.get("text_metrics", "cap") == "cap" and _local(el) == "text":
                    cap_ids.add(id_)
        boxes, caps = self.measure(doc, sorted(cap_ids))

        def eff(id_: str) -> layout.Box:
            if id_ not in boxes:
                raise DocumentError(f"{id_!r} has no visible geometry to align.")
            x, y, w, h = boxes[id_]
            if id_ in caps:
                _, y, _, h = caps[id_]
            return x, y, w, h

        def descendants(id_: str) -> list[str]:
            return [e.get("id") for e in doc.get(id_).iter() if isinstance(e.tag, str) and e.get("id")]

        total: dict[str, list[float]] = {}
        for op in operations:
            ids, to = list(op["ids"]), op.get("to", "page")
            if to == "page":
                ref = doc.viewbox
            elif to == "selection":
                ref = layout.union([eff(i) for i in ids])
            else:
                ref = eff(to)
            h, v, m = op.get("horizontal"), op.get("vertical"), float(op.get("margin") or 0)
            if op.get("as_group"):
                d = layout.align_delta(layout.union([eff(i) for i in ids]), ref, h, v, m)
                deltas = {i: d for i in ids}
            else:
                deltas = {i: layout.align_delta(eff(i), ref, h, v, m) for i in ids}
            for id_, (dx, dy) in deltas.items():
                t = total.setdefault(id_, [0.0, 0.0])
                t[0] += dx
                t[1] += dy
                for sub in descendants(id_):  # keep the cache true for later operations
                    for cache in (boxes, caps):
                        if sub in cache:
                            cache[sub] = layout.shift(cache[sub], dx, dy)
        self.translate(doc, {k: (v[0], v[1]) for k, v in total.items()})
        moved = {k: [round(v[0], 3), round(v[1], 3)] for k, v in total.items() if abs(v[0]) + abs(v[1]) > 1e-9}
        return {"moved": moved, "bboxes": {k: [round(c, 2) for c in boxes[k]] for k in total if k in boxes}}

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
