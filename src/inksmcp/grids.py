"""Pure tick maths for grid/graph-paper axes. No lxml, no Inkscape.

A tick is (offset from the axis origin in user units, weight class, label or None).
Weight classes: "major" > "medium" > "minor".
"""
from __future__ import annotations

import math
from typing import Any

CLASSES = ("minor", "medium", "major")
# What stationery log paper uses per cycle: (from, to, step) — field report 2026-09-27
LOG_SUBDIVISIONS = {
    "standard": [(1, 2, 0.1), (2, 5, 0.2), (5, 10, 0.5)],
    "fine": [(1, 2, 0.05), (2, 5, 0.1), (5, 10, 0.2)],
    "integers": [],
}
_EPS = 1e-6


def _fmt(v: float) -> str:
    return f"{round(v, 6):g}"


def linear_ticks(length: float, major: float, medium: float | None = None, minor: float | None = None,
                 label_start: float = 0, label_step: float = 1) -> list[tuple[float, str, str | None]]:
    """Lines every `minor`/`medium`/`major` user units from 0 to `length`. Majors are labelled
    label_start, label_start + label_step, ..."""
    for name, v in (("major", major), ("medium", medium), ("minor", minor)):
        if v is not None and v <= 0:
            raise ValueError(f"{name} spacing must be > 0")
    finest = min(v for v in (major, medium, minor) if v)
    if length / finest > 5000:
        raise ValueError("Too many grid lines (> 5000 on one axis); use a larger spacing.")

    def multiple(pos: float, step: float | None) -> bool:
        return bool(step) and abs(pos / step - round(pos / step)) < 1e-6 * max(1.0, pos / step)

    ticks = []
    n = int(math.floor(length / finest + _EPS))
    for i in range(n + 1):
        pos = i * finest
        if multiple(pos, major):
            k = round(pos / major)
            ticks.append((pos, "major", _fmt(label_start + k * label_step)))
        elif multiple(pos, medium):
            ticks.append((pos, "medium", None))
        else:
            ticks.append((pos, "minor", None))
    return ticks


def log_ticks(length: float, cycles: int, subdivisions: str = "standard") -> list[tuple[float, str, str | None]]:
    """Log-scale lines over `cycles` decades: decades major, 2..9 medium, subdivisions minor.
    Labels: 1..9 in each cycle and 1 at every decade line (as on printed log paper)."""
    if cycles < 1 or cycles > 12:
        raise ValueError("cycles must be between 1 and 12")
    if subdivisions not in LOG_SUBDIVISIONS:
        raise ValueError(f"subdivisions must be one of {sorted(LOG_SUBDIVISIONS)}")
    cycle = length / cycles
    values: dict[float, str] = {}
    for a, b, step in LOG_SUBDIVISIONS[subdivisions]:
        for i in range(int(round((b - a) / step)) + 1):
            values.setdefault(round(a + i * step, 6), "minor")
    for v in range(1, 10):
        values[float(v)] = "medium"
    values[1.0] = "major"
    ticks = []
    for c in range(cycles):
        for v, cls in sorted(values.items()):
            if v >= 10 - _EPS:
                continue
            label = str(int(v)) if abs(v - round(v)) < _EPS else None
            ticks.append((c * cycle + math.log10(v) * cycle, cls, label))
    ticks.append((length, "major", "1"))
    return ticks


def axis_mapper(spec: dict[str, Any], length: float):
    """value -> offset along the axis (user units from the axis origin), the inverse of the ticks:
    linear: label_start sits at 0 and each major step adds label_step;
    log: `start` (default 1) sits at 0 and each cycle is one decade."""
    spec = dict(spec)
    spec.pop("reverse", None)
    scale = spec.get("scale", "linear")
    if scale == "log":
        cycles = int(spec.get("cycles", 1))
        start = float(spec.get("start", 1))

        def f(v: float) -> float:
            if v <= 0:
                raise ValueError(f"{v} cannot be shown on a log axis")
            return math.log10(v / start) * length / cycles
        return f
    major = float(spec["major"])
    label_start, label_step = float(spec.get("label_start", 0)), float(spec.get("label_step", 1))
    return lambda v: (v - label_start) / label_step * major


def axis_ticks(spec: dict[str, Any], length: float) -> list[tuple[float, str, str | None]]:
    spec = dict(spec)
    scale = spec.pop("scale", "linear")
    try:
        if scale == "log":
            allowed = {"cycles", "subdivisions", "start"}
            _no_extra(spec, allowed, scale)
            return log_ticks(length, int(spec.get("cycles", 1)), spec.get("subdivisions", "standard"))
        if scale == "linear":
            _no_extra(spec, {"major", "medium", "minor", "label_start", "label_step"}, scale)
            if "major" not in spec:
                raise ValueError("a linear axis needs 'major' (spacing of the heaviest lines)")
            return linear_ticks(length, float(spec["major"]), spec.get("medium"), spec.get("minor"),
                                float(spec.get("label_start", 0)), float(spec.get("label_step", 1)))
    except TypeError as e:
        raise ValueError(str(e)) from e
    raise ValueError("scale must be 'linear' or 'log'")


def _no_extra(spec: dict, allowed: set, scale: str) -> None:
    extra = set(spec) - allowed
    if extra:
        raise ValueError(f"unknown keys for a {scale} axis: {sorted(extra)}; allowed: {sorted(allowed)}")
