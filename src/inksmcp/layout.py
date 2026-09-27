"""Pure layout maths on boxes (x, y, width, height) in user units. No Inkscape, no lxml."""
from __future__ import annotations

import math
import re
from typing import Literal, Optional

Box = tuple[float, float, float, float]
Horizontal = Optional[Literal["left", "center", "right"]]
Vertical = Optional[Literal["top", "middle", "bottom"]]


def union(boxes: list[Box]) -> Box:
    if not boxes:
        raise ValueError("union of no boxes")
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[0] + b[2] for b in boxes)
    y1 = max(b[1] + b[3] for b in boxes)
    return x0, y0, x1 - x0, y1 - y0


def shift(box: Box, dx: float, dy: float) -> Box:
    return box[0] + dx, box[1] + dy, box[2], box[3]


def align_delta(box: Box, ref: Box, horizontal: Horizontal = None, vertical: Vertical = None,
                margin: float = 0.0) -> tuple[float, float]:
    """Translation that aligns `box` to `ref`. `margin` insets from the reference edge (ignored for centre)."""
    x, y, w, h = box
    rx, ry, rw, rh = ref
    dx = dy = 0.0
    if horizontal == "left":
        dx = rx + margin - x
    elif horizontal == "center":
        dx = (rx + rw / 2) - (x + w / 2)
    elif horizontal == "right":
        dx = (rx + rw - margin) - (x + w)
    elif horizontal is not None:
        raise ValueError(f"horizontal must be left/center/right, not {horizontal!r}")
    if vertical == "top":
        dy = ry + margin - y
    elif vertical == "middle":
        dy = (ry + rh / 2) - (y + h / 2)
    elif vertical == "bottom":
        dy = (ry + rh - margin) - (y + h)
    elif vertical is not None:
        raise ValueError(f"vertical must be top/middle/bottom, not {vertical!r}")
    return dx, dy


Align = Literal["start", "center", "end"]


def _place(size: float, cell: float, align: Align) -> float:
    return {"start": 0.0, "center": (cell - size) / 2, "end": cell - size}[align]


def arrange(sizes: list[tuple[float, float]], direction: Literal["row", "column", "grid"] = "row",
            gap: float | tuple[float, float] = 0.0, columns: int | None = None,
            align: Align = "center") -> tuple[list[tuple[float, float]], tuple[float, float]]:
    """Top-left position of each item relative to the block origin, and the block size.

    row/column: items follow each other with `gap`; `align` positions them on the cross axis.
    grid: `columns` per row; column widths/row heights fit their largest item; `align` applies
    within each cell on both axes.
    """
    if align not in ("start", "center", "end"):
        raise ValueError(f"align must be start/center/end, not {align!r}")
    gx, gy = (gap, gap) if isinstance(gap, (int, float)) else gap
    n = len(sizes)
    if direction == "row":
        columns = n
    elif direction == "column":
        columns = 1
    elif direction == "grid":
        columns = columns or max(1, math.ceil(math.sqrt(n)))
    else:
        raise ValueError(f"direction must be row/column/grid, not {direction!r}")
    rows = math.ceil(n / columns) if n else 0
    col_w = [max((sizes[i][0] for i in range(c, n, columns)), default=0.0) for c in range(columns)]
    row_h = [max((sizes[i][1] for i in range(r * columns, min(n, (r + 1) * columns))), default=0.0)
             for r in range(rows)]
    xs = [sum(col_w[:c]) + gx * c for c in range(columns)]
    ys = [sum(row_h[:r]) + gy * r for r in range(rows)]
    out = []
    for i, (w, h) in enumerate(sizes):
        r, c = divmod(i, columns)
        if direction == "row":  # main axis packs tightly; only the cross axis aligns
            out.append((xs[c], _place(h, row_h[0], align)))
        elif direction == "column":
            out.append((_place(w, col_w[0], align), ys[r]))
        else:
            out.append((xs[c] + _place(w, col_w[c], align), ys[r] + _place(h, row_h[r], align)))
    width = sum(col_w) + gx * max(0, columns - 1) if n else 0.0
    height = sum(row_h) + gy * max(0, rows - 1) if n else 0.0
    return out, (width, height)


_PATH_TOKEN = re.compile(r"[MmLlHhVvZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def polyline_points(d: str) -> list[tuple[float, float]]:
    """Vertices of a path made of straight segments (M/L/H/V/Z, absolute or relative)."""
    pts: list[tuple[float, float]] = []
    x = y = 0.0
    cmd = None
    nums: list[float] = []
    tokens = _PATH_TOKEN.findall(d or "")
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t.isalpha():
            cmd = t
            i += 1
            if cmd in "Zz" and pts:
                pts.append(pts[0])
            continue
        need = 1 if cmd in "HhVv" else 2
        nums = [float(v) for v in tokens[i:i + need]]
        i += need
        if cmd in "Mm":
            # a leading relative moveto is absolute (SVG spec)
            x, y = (x + nums[0], y + nums[1]) if cmd == "m" and pts else (nums[0], nums[1])
            cmd = "l" if cmd == "m" else "L"  # implicit lineto after moveto
        elif cmd == "L":
            x, y = nums
        elif cmd == "l":
            x, y = x + nums[0], y + nums[1]
        elif cmd == "H":
            x = nums[0]
        elif cmd == "h":
            x += nums[0]
        elif cmd == "V":
            y = nums[0]
        elif cmd == "v":
            y += nums[0]
        else:
            raise ValueError(f"Unsupported path command {cmd!r} in {d!r}")
        pts.append((x, y))
    return pts


def polyline_midpoint(pts: list[tuple[float, float]]) -> tuple[float, float, float]:
    """Point halfway along the polyline and the direction (radians) of the segment there."""
    segs = [(a, b, math.dist(a, b)) for a, b in zip(pts, pts[1:])]
    total = sum(s[2] for s in segs)
    if not segs or total == 0:
        p = pts[0] if pts else (0.0, 0.0)
        return p[0], p[1], 0.0
    half = total / 2
    for (ax, ay), (bx, by), length in segs:
        if half <= length and length > 0:
            f = half / length
            return ax + (bx - ax) * f, ay + (by - ay) * f, math.atan2(by - ay, bx - ax)
        half -= length
    (ax, ay), (bx, by), _ = segs[-1]
    return bx, by, math.atan2(by - ay, bx - ax)
