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


def split(box: Box, rows: list, heights: list[float] | None, gutter: tuple[float, float]) -> list[list[Box]]:
    """Cells of a region: rows (heights as ratios) each split into columns by ratios, with gutters
    between cells (not at the edges). A row is a list of column ratios or a number of equal columns."""
    x, y, w, h = box
    gx, gy = gutter
    specs = [[1.0] * int(r) if isinstance(r, (int, float)) else [float(v) for v in r] for r in rows]
    if not specs or any(not r or any(v <= 0 for v in r) for r in specs):
        raise ValueError("rows must be column counts or lists of positive ratios, e.g. [[2, 1], 3].")
    hr = [float(v) for v in heights] if heights else [1.0] * len(specs)
    if len(hr) != len(specs) or any(v <= 0 for v in hr):
        raise ValueError("heights needs one positive ratio per row.")
    free_h = h - gy * (len(specs) - 1)
    if free_h <= 0:
        raise ValueError("the gutters leave no height for the rows.")
    out, cy = [], y
    for ratios, hv in zip(specs, hr):
        rh = free_h * hv / sum(hr)
        free_w = w - gx * (len(ratios) - 1)
        if free_w <= 0:
            raise ValueError("the gutters leave no width for the columns.")
        cx, row = x, []
        for r in ratios:
            cw = free_w * r / sum(ratios)
            row.append((round(cx, 4), round(cy, 4), round(cw, 4), round(rh, 4)))
            cx += cw + gx
        out.append(row)
        cy += rh + gy
    return out


# -- orthogonal routing for connectors with sides / waypoints ----------------------------------
Point = tuple[float, float]
SIDES = {"top": (0.0, -1.0), "right": (1.0, 0.0), "bottom": (0.0, 1.0), "left": (-1.0, 0.0)}


def side_point(box: Box, side: str) -> Point:
    x, y, w, h = box
    return {"top": (x + w / 2, y), "right": (x + w, y + h / 2), "bottom": (x + w / 2, y + h),
            "left": (x, y + h / 2)}[side]


def auto_sides(a: Box, b: Box) -> tuple[str, str]:
    """Facing sides of two boxes (the dominant axis between their centres)."""
    dx = (b[0] + b[2] / 2) - (a[0] + a[2] / 2)
    dy = (b[1] + b[3] / 2) - (a[1] + a[3] / 2)
    if abs(dx) >= abs(dy):
        return ("right", "left") if dx >= 0 else ("left", "right")
    return ("bottom", "top") if dy >= 0 else ("top", "bottom")


def _simplify(pts: list[Point]) -> list[Point]:
    out: list[Point] = []
    for p in pts:
        if out and math.dist(out[-1], p) < 1e-9:
            continue
        if len(out) >= 2:
            (ax, ay), (bx, by) = out[-2], out[-1]
            if abs((bx - ax) * (p[1] - ay) - (by - ay) * (p[0] - ax)) < 1e-9:  # collinear
                out[-1] = p
                continue
        out.append(p)
    return out


def _crosses(p: Point, q: Point, box: Box, eps: float = 1e-6) -> bool:
    """Does the axis-aligned segment p-q pass through the interior of box?"""
    x, y, w, h = box
    x0, x1 = sorted((p[0], q[0]))
    y0, y1 = sorted((p[1], q[1]))
    return x0 < x + w - eps and x1 > x + eps and y0 < y + h - eps and y1 > y + eps


def route_elbow(a: Box, b: Box, from_side: str, to_side: str, stub: float) -> list[Point]:
    """Orthogonal route leaving `a` through `from_side` and entering `b` through `to_side`.
    Tries 0–2 corner candidates, rejects ones that double back or cut through either box,
    returns the shortest (fewest corners on ties)."""
    s, e = side_point(a, from_side), side_point(b, to_side)
    ds, de = SIDES[from_side], SIDES[to_side]
    s1 = (s[0] + ds[0] * stub, s[1] + ds[1] * stub)
    e1 = (e[0] + de[0] * stub, e[1] + de[1] * stub)
    mx, my = (s1[0] + e1[0]) / 2, (s1[1] + e1[1]) / 2
    candidates = [
        [s, s1, (e1[0], s1[1]), e1, e], [s, s1, (s1[0], e1[1]), e1, e],
        [s, s1, (mx, s1[1]), (mx, e1[1]), e1, e], [s, s1, (s1[0], my), (e1[0], my), e1, e],
    ]
    best, best_score = None, math.inf
    for c in candidates:
        pts = _simplify(c)
        segs = list(zip(pts, pts[1:]))
        score = sum(math.dist(p, q) for p, q in segs) + 0.01 * len(pts)
        first = (pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
        last = (pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1])
        if first[0] * ds[0] + first[1] * ds[1] <= 0 or last[0] * de[0] + last[1] * de[1] >= 0:
            score += 1e6  # leaves or enters through the wrong side
        if any(_crosses(p, q, a) or _crosses(p, q, b) for p, q in segs):
            score += 1e5
        if score < best_score:
            best, best_score = pts, score
    return best


def route(a: Box, b: Box, from_side: str | None, to_side: str | None, via: list[Point] | None,
          routing: str, stub: float) -> list[Point]:
    auto_from, auto_to = auto_sides(a, b)
    fs, ts = from_side or auto_from, to_side or auto_to
    if via:
        return _simplify([side_point(a, fs)] + [tuple(v) for v in via] + [side_point(b, ts)])
    if routing == "elbow":
        return route_elbow(a, b, fs, ts, stub)
    return [side_point(a, fs), side_point(b, ts)]


def trim_ends(pts: list[Point], start: float = 0.0, end: float = 0.0) -> list[Point]:
    """Pull the route's ends back along their segments, leaving a gap at each end (field report 6:
    arrowheads touching the target text). A segment is never shortened by more than 90 %."""
    pts = list(pts)
    for idx, nxt, gap in ((0, 1, start), (-1, -2, end)):
        if gap and len(pts) >= 2:
            (x0, y0), (x1, y1) = pts[idx], pts[nxt]
            length = math.dist((x0, y0), (x1, y1))
            if length > 0:
                t = min(gap, 0.9 * length) / length
                pts[idx] = (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
    return pts


def _n4(v: float) -> str:
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def polyline_d(pts: list[Point]) -> str:
    return "M " + " L ".join(f"{_n4(x)},{_n4(y)}" for x, y in pts)


def polyline_at(pts: list[Point], t: float | None) -> tuple[float, float, float]:
    """Point and direction at fraction t of the length; t=None → middle of the longest segment
    (a label there never sits on a corner — field report 2)."""
    segs = [(p, q, math.dist(p, q)) for p, q in zip(pts, pts[1:])]
    if not segs:
        return (*pts[0], 0.0) if pts else (0.0, 0.0, 0.0)
    if t is None:
        p, q, _ = max(segs, key=lambda s: s[2])
        return (p[0] + q[0]) / 2, (p[1] + q[1]) / 2, math.atan2(q[1] - p[1], q[0] - p[0])
    total = sum(s[2] for s in segs)
    d = max(0.0, min(1.0, t)) * total
    for p, q, length in segs:
        if d <= length and length > 0:
            f = d / length
            return p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f, math.atan2(q[1] - p[1], q[0] - p[0])
        d -= length
    p, q, _ = segs[-1]
    return q[0], q[1], math.atan2(q[1] - p[1], q[0] - p[0])


# -- affine transforms (SVG convention: (a, b, c, d, e, f) = [a c e; b d f; 0 0 1]) ------------
Matrix = tuple[float, float, float, float, float, float]
IDENTITY: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
_TRANSFORM = re.compile(r"(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)")


def mat_mul(m: Matrix, n: Matrix) -> Matrix:
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + c * B, b * A + d * B, a * C + c * D, b * C + d * D, a * E + c * F + e, b * E + d * F + f)


def mat_inv(m: Matrix) -> Matrix:
    a, b, c, d, e, f = m
    det = a * d - b * c
    if abs(det) < 1e-12:
        raise ValueError("transform is not invertible")
    return (d / det, -b / det, -c / det, a / det, (c * f - d * e) / det, (b * e - a * f) / det)


def parse_transform(value: str | None) -> Matrix:
    m = IDENTITY
    for name, args in _TRANSFORM.findall(value or ""):
        v = [float(x) for x in re.split(r"[\s,]+", args.strip()) if x]
        if name == "matrix" and len(v) == 6:
            t = tuple(v)
        elif name == "translate":
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == "scale":
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "rotate":
            r = math.radians(v[0])
            t = (math.cos(r), math.sin(r), -math.sin(r), math.cos(r), 0, 0)
            if len(v) == 3:
                t = mat_mul(mat_mul((1, 0, 0, 1, v[1], v[2]), t), (1, 0, 0, 1, -v[1], -v[2]))
        elif name == "skewX":
            t = (1, 0, math.tan(math.radians(v[0])), 1, 0, 0)
        elif name == "skewY":
            t = (1, math.tan(math.radians(v[0])), 0, 1, 0, 0)
        else:
            raise ValueError(f"bad transform {name}({args})")
        m = mat_mul(m, t)
    return m


def format_transform(m: Matrix, decimals: int = 6) -> str:
    """Shortest SVG form: '' for identity, translate() when possible, else matrix()."""
    def n(v: float) -> str:
        s = f"{round(v, decimals):.{decimals}f}".rstrip("0").rstrip(".")
        return "0" if s in ("", "-0") else s

    a, b, c, d, e, f = m
    if all(abs(x - y) < 10 ** -decimals for x, y in zip((a, b, c, d), (1, 0, 0, 1))):
        if abs(e) < 10 ** -decimals and abs(f) < 10 ** -decimals:
            return ""
        return f"translate({n(e)},{n(f)})"
    return f"matrix({','.join(n(x) for x in m)})"