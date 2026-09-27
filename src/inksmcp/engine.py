"""Inkscape-backed operations on a Document: geometry queries, actions, export, preview.

The Document (lxml) is the source of truth. For each operation we hand Inkscape a
temp copy through the persistent shell, then close it again.
"""
from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path

from .document import Document
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
