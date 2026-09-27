"""Pure layout maths on boxes (x, y, width, height) in user units. No Inkscape, no lxml."""
from __future__ import annotations

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
