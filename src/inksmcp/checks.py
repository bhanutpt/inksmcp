"""Layout checks (D-024 step 2): what agents found by zooming in 6 of 7 round-2 reports.

Pure geometry on measured boxes (document coordinates) and line segments; no lxml, no Inkscape.
Three findings, each for pairs where at least one element was touched by the call:
  - two texts overlap;
  - a text crosses the edge of a rect / circle / ellipse / image (inside it is fine, e.g. a card label);
  - a text without a halo is crossed by a stroked line or outline (a halo means "on purpose").
A pair is skipped when an opaque shape painted between them covers the text: what lies under a balloon or
caption box can't collide with the text on it (E29).
"""
from __future__ import annotations

import re

Box = tuple[float, float, float, float]
Seg = tuple[tuple[float, float], tuple[float, float]]
MAX_WARNINGS = 12

_TOKEN = re.compile(r"[A-Za-z]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def path_segments(d: str) -> list[Seg]:
    """Straight segments of a path, subpaths kept apart. Curves raise ValueError (not checked)."""
    segs: list[Seg] = []
    x = y = sx = sy = 0.0
    cmd = None
    tokens = _TOKEN.findall(d or "")
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t.isalpha():
            cmd = t
            i += 1
            if cmd in "Zz":
                if (x, y) != (sx, sy):
                    segs.append(((x, y), (sx, sy)))
                x, y = sx, sy
            elif cmd not in "MmLlHhVv":
                raise ValueError(f"curve command {cmd!r}")
            continue
        need = 1 if cmd in "HhVv" else 2
        n = [float(v) for v in tokens[i:i + need]]
        i += need
        px, py = x, y
        if cmd in "Mm":
            x, y = (x + n[0], y + n[1]) if cmd == "m" else (n[0], n[1])
            sx, sy = x, y
            cmd = "l" if cmd == "m" else "L"
            continue
        if cmd == "L":
            x, y = n
        elif cmd == "l":
            x, y = x + n[0], y + n[1]
        elif cmd == "H":
            x = n[0]
        elif cmd == "h":
            x += n[0]
        elif cmd == "V":
            y = n[0]
        elif cmd == "v":
            y += n[0]
        segs.append(((px, py), (x, y)))
    return segs


def intersection(a: Box, b: Box) -> tuple[float, float]:
    """Width and height of the overlap of two boxes (<= 0 when apart)."""
    return (min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]), min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))


def inside(a: Box, b: Box, tol: float) -> bool:
    """a lies within b."""
    return (a[0] >= b[0] - tol and a[1] >= b[1] - tol and a[0] + a[2] <= b[0] + b[2] + tol
            and a[1] + a[3] <= b[1] + b[3] + tol)


def segment_hits(p, q, box: Box, shrink: float) -> bool:
    """Does segment p-q pass through the box (shrunk by `shrink` on each side)? Liang–Barsky."""
    x0, y0 = box[0] + shrink, box[1] + shrink
    x1, y1 = box[0] + box[2] - shrink, box[1] + box[3] - shrink
    if x1 <= x0 or y1 <= y0:
        return False
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for pk, qk in ((-dx, p[0] - x0), (dx, x1 - p[0]), (-dy, p[1] - y0), (dy, y1 - p[1])):
        if pk == 0:
            if qk < 0:
                return False
            continue
        r = qk / pk
        if pk < 0:
            t0 = max(t0, r)
        else:
            t1 = min(t1, r)
        if t0 > t1:
            return False
    return True


def covers(shape: tuple, box: Box) -> bool:
    """Does an opaque shape cover the whole box? shape = (kind, local geometry, inverse CTM); the box is in
    document coordinates. kind: rect (x, y, w, h, rx, ry), ellipse (cx, cy, rx, ry), polygon (points)."""
    kind, g, inv = shape
    a, b, c, d, e, f = inv
    pts = [(a * x + c * y + e, b * x + d * y + f)
           for x, y in ((box[0], box[1]), (box[0] + box[2], box[1]), (box[0], box[1] + box[3]),
                        (box[0] + box[2], box[1] + box[3]))]
    if kind == "rect":
        x0, y0, w, h, rx, ry = g
        for px, py in pts:
            if not (x0 <= px <= x0 + w and y0 <= py <= y0 + h):
                return False
            if rx > 0 and ry > 0:  # in a rounded corner's square: inside the arc?
                cx = x0 + rx if px < x0 + rx else x0 + w - rx if px > x0 + w - rx else None
                cy = y0 + ry if py < y0 + ry else y0 + h - ry if py > y0 + h - ry else None
                if cx is not None and cy is not None and ((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2 > 1:
                    return False
        return True
    if kind == "ellipse":  # convex: the corners inside means the box inside
        cx, cy, rx, ry = g
        return rx > 0 and ry > 0 and all(((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2 <= 1 for px, py in pts)
    poly = g  # even-odd point test on the corners, and no edge through the box (non-convex outlines)
    for px, py in pts:
        hit = False
        for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
            if (y1 > py) != (y2 > py) and px < x1 + (py - y1) * (x2 - x1) / (y2 - y1):
                hit = not hit
        if not hit:
            return False
    lx, ly = min(p[0] for p in pts), min(p[1] for p in pts)
    local = (lx, ly, max(p[0] for p in pts) - lx, max(p[1] for p in pts) - ly)
    return not any(segment_hits(p, q, local, 0) for p, q in zip(poly, poly[1:] + poly[:1]))


def _grouped(found: list[tuple[str, str]], one: str, many: str) -> list[str]:
    """One line per text: a pattern behind an uncovered text is one finding, not twenty."""
    by: dict[str, list[str]] = {}
    for t, s in found:
        by.setdefault(t, []).append(s)
    out = []
    for t, ss in by.items():
        if len(ss) == 1:
            out.append(one.format(t=t, s=ss[0]))
        else:
            names = ", ".join(repr(s) for s in ss[:3]) + (f" (+{len(ss) - 3} more)" if len(ss) > 3 else "")
            out.append(many.format(t=t, n=len(ss), s=names))
    return out


def stacked(boxes: dict[str, Box], points: dict[str, tuple[float, float]], tol: float) -> set[str]:
    """Elements dropped on one spot to be arranged later (the workflow the server recommends): three or
    more sharing a box top-left corner, a box centre, or (texts) an anchor point. Their overlaps are
    expected, not findings."""
    groups: dict[tuple, set[str]] = {}
    q = max(tol, 1e-6)
    for i, (x, y, w, h) in boxes.items():
        keys = [("tl", round(x / q), round(y / q)), ("c", round((x + w / 2) / q), round((y + h / 2) / q))]
        if i in points:
            keys.append(("a", round(points[i][0] / q), round(points[i][1] / q)))
        for key in keys:
            groups.setdefault(key, set()).add(i)
    return set().union(*(g for g in groups.values() if len(g) >= 3)) if groups else set()


def find(texts: dict[str, Box], areas: dict[str, Box], lines: dict[str, tuple[Box, list[Seg], float]],
         touched: set[str], haloed: set[str], skip_pairs: set[frozenset], tol: float,
         anchors: dict[str, tuple[float, float]] | None = None, order: dict[str, int] | None = None,
         cover: dict[str, int] | None = None) -> list[str]:
    """Warnings, most useful first; at most MAX_WARNINGS plus a count of the rest. `anchors`: the
    x/y points of texts (their glyph boxes differ, their anchors match when they are stacked).
    `order`: paint order; `cover[t]`: the paint order of the topmost opaque shape covering text t."""
    pile = stacked({**texts, **areas, **{k: v[0] for k, v in lines.items()}}, anchors or {}, tol)
    order, cover = order or {}, cover or {}

    def hidden(t: str, other: str) -> bool:  # `other` is painted under an opaque shape that covers t
        return t in cover and order.get(other, cover[t]) < cover[t]

    def wanted(a: str, b: str) -> bool:
        return ((a in touched or b in touched) and frozenset((a, b)) not in skip_pairs
                and not (a in pile and b in pile) and not hidden(a, b) and not hidden(b, a))

    out: list[str] = []
    tids = sorted(texts)
    for n, a in enumerate(tids):
        for b in tids[n + 1:]:
            if wanted(a, b):
                w, h = intersection(texts[a], texts[b])
                if w > tol and h > tol:
                    out.append(f"text {a!r} overlaps text {b!r} ({w:.1f} x {h:.1f}).")
    edges = []
    top_first = sorted(areas, key=lambda s: -order.get(s, 0))  # a text's own box before what lies under it
    for t in tids:
        for s in top_first:
            box = areas[s]
            if wanted(t, s):
                w, h = intersection(texts[t], box)
                if w > tol and h > tol and not inside(texts[t], box, tol) and not inside(box, texts[t], tol):
                    edges.append((t, s))
    out += _grouped(edges, "text {t!r} crosses the edge of {s!r}.", "text {t!r} crosses the edges of {n} shapes: {s}.")
    crossed = []
    for t in tids:
        if t in haloed:
            continue
        for s in sorted(lines, key=lambda s: -order.get(s, 0)):
            box, segs, width = lines[s]
            if not wanted(t, s):
                continue
            if width >= texts[t][3] and inside(texts[t], box, tol):
                continue  # a label ON a thick stroke (a bar's value), not crossed by it
            w, h = intersection(texts[t], box)
            if w > -tol and h > -tol and any(segment_hits(p, q, texts[t], tol) for p, q in segs):
                crossed.append((t, s))
    out += _grouped(crossed, "text {t!r} is crossed by {s!r} (give it a halo if that is intended).",
                    "text {t!r} is crossed by {n} lines: {s} (give it a halo if that is intended).")
    if len(out) > MAX_WARNINGS:
        out = out[:MAX_WARNINGS] + [f"... and {len(out) - MAX_WARNINGS} more overlaps."]
    piled = sorted(pile & touched)
    if piled:
        more = f" (+{len(piled) - 4})" if len(piled) > 4 else ""
        out.append(f"{len(piled)} elements are stacked on one spot ({', '.join(piled[:4])}{more}): "
                   "not checked against each other until arranged.")
    return out
