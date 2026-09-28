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


def _every(coarse: float, fine: float, names: str) -> int:
    """How many `fine` steps make one `coarse` step. Spacings typed as rounded decimals
    (11.6667 / 2.3333) are accepted within 0.1 %; anything else is an error, not silently
    missing lines (field report 10)."""
    n = round(coarse / fine)
    if n < 1 or abs(coarse / fine - n) > 1e-3 * n:
        raise ValueError(f"{names}: {coarse:g} is not a whole multiple of {fine:g}")
    return n


def linear_ticks(length: float, major: float, medium: float | None = None, minor: float | None = None,
                 label_start: float = 0, label_step: float = 1) -> list[tuple[float, str, str | None]]:
    """Lines every `minor`/`medium`/`major` user units from 0 to `length`. Majors are labelled
    label_start, label_start + label_step, ... Lines are classed by index, and placed at exact
    fractions of `major` (the spacing `plot` maps data with)."""
    for name, v in (("major", major), ("medium", medium), ("minor", minor)):
        if v is not None and v <= 0:
            raise ValueError(f"{name} spacing must be > 0")
    finer = [v for v in (medium, minor) if v]
    finest = min(finer) if finer else major
    if finest > major:
        raise ValueError("medium/minor spacing must not be larger than major")
    if length / finest > 5000:
        raise ValueError("Too many grid lines (> 5000 on one axis); use a larger spacing.")
    major_n = _every(major, finest, "major")
    medium_n = _every(medium, finest, "medium") if medium else None
    if medium_n and major_n % medium_n:
        raise ValueError(f"major: {major:g} is not a whole multiple of medium {medium:g}")
    step = major / major_n
    ticks = []
    n = int(math.floor(length / step * (1 + 1e-4)))  # a line within 0.01 % of the edge is on it
    for i in range(n + 1):
        pos = min(i * step, length)
        if i % major_n == 0:
            ticks.append((pos, "major", _fmt(label_start + i // major_n * label_step)))
        elif medium_n and i % medium_n == 0:
            ticks.append((pos, "medium", None))
        else:
            ticks.append((pos, "minor", None))
    return ticks


def _plain(v: float) -> str:
    """10, 1000000, 0.001 — no exponent notation for decade labels."""
    return str(int(round(v))) if v >= 1 else f"{v:.12f}".rstrip("0")


def log_ticks(length: float, cycles: int, subdivisions: str = "standard", start: float = 1,
              labels: str = "paper") -> list[tuple[float, str, str | None]]:
    """Log-scale lines over `cycles` decades: decades major, 2..9 medium, subdivisions minor.
    labels "paper": 1..9 in each cycle and 1 at every decade line (as on printed log paper);
    "decades": the decade values start, start*10, ... (what `plot` maps data with)."""
    if labels not in ("paper", "decades"):
        raise ValueError('log labels must be "paper" or "decades"')
    if start <= 0:
        raise ValueError("log start must be > 0")
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
            if labels == "decades":
                label = _plain(start * 10 ** c) if v == 1.0 else None
            else:
                label = str(int(v)) if abs(v - round(v)) < _EPS else None
            ticks.append((c * cycle + math.log10(v) * cycle, cls, label))
    ticks.append((length, "major", _plain(start * 10 ** cycles) if labels == "decades" else "1"))
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
            allowed = {"cycles", "subdivisions", "start", "labels"}
            _no_extra(spec, allowed, scale)
            # a given start means data values: label the decades with them (field report 10)
            return log_ticks(length, int(spec.get("cycles", 1)), spec.get("subdivisions", "standard"),
                             float(spec.get("start", 1)), spec.get("labels", "decades" if "start" in spec else "paper"))
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
