"""Pure template stamping for `repeat`: placeholders and id mapping. No lxml, no Inkscape.

A template is a list of element specs. `{key}` in any string is replaced from the row; a string that
is exactly one placeholder takes the row value as is (so numbers stay numbers). `{i}` is the 0-based
row index, `{n}` the 1-based row number; `{{` / `}}` are literal braces.
Template ids are local names: "card" becomes "card-<n>" unless the id has a placeholder of its own.
"""
from __future__ import annotations

import re
from typing import Any

_TOKEN = re.compile(r"\{\{|\}\}|\{(\w+)\}")
_SINGLE = re.compile(r"\{(\w+)\}")
RESERVED = {"i", "n"}
MIRROR_MODES = {"reflect", "block", "none"}


def fill(value: Any, ctx: dict[str, Any]) -> Any:
    if isinstance(value, str):
        m = _SINGLE.fullmatch(value)
        if m:
            return _lookup(m.group(1), ctx)

        def sub(t: re.Match) -> str:
            if t.group(0) in ("{{", "}}"):
                return t.group(0)[0]
            return str(_lookup(t.group(1), ctx))
        return _TOKEN.sub(sub, value)
    if isinstance(value, list):
        return [fill(v, ctx) for v in value]
    if isinstance(value, dict):
        return {k: fill(v, ctx) for k, v in value.items()}
    return value


def _lookup(key: str, ctx: dict[str, Any]) -> Any:
    if key not in ctx:
        raise ValueError(f"placeholder {{{key}}} has no value; row keys: {sorted(set(ctx) - RESERVED)}")
    return ctx[key]


def stamp(template: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[list[tuple[str, dict[str, Any], str]]]:
    """Per row: (template name, filled spec, mirror mode) in template order. Parents that name
    another template element are mapped to that element's stamped id; a missing parent means the
    row group (filled in by the caller). Names are the raw template ids, or '#<index>' without one."""
    if not template:
        raise ValueError("template needs at least one element")
    if not rows:
        raise ValueError("rows needs at least one row")
    names = []
    for k, spec in enumerate(template):
        if not isinstance(spec, dict) or "type" not in spec:
            raise ValueError(f"template[{k}] must be an element spec with a 'type'")
        if "layer" in spec:
            raise ValueError(f"template[{k}]: elements live in their row group; set `layer` on repeat instead")
        if spec.get("mirror", "reflect") not in MIRROR_MODES:
            raise ValueError(f"template[{k}]: mirror must be one of {sorted(MIRROR_MODES)}")
        names.append(spec.get("id") or f"#{k}")
    if len(set(names)) != len(names):
        raise ValueError("template ids must be unique")
    out = []
    for i, row in enumerate(rows):
        clash = RESERVED & set(row)
        if clash:
            raise ValueError(f"rows[{i}]: {sorted(clash)} are reserved (row index / number)")
        ctx = {**row, "i": i, "n": i + 1}
        ids = {}
        for name, spec in zip(names, template):
            raw = spec.get("id")
            if raw:
                ids[name] = fill(raw, ctx) if _SINGLE.search(raw) else f"{raw}-{i + 1}"
        stamped = []
        for k, (name, spec) in enumerate(zip(names, template)):
            s = {key: val for key, val in spec.items() if key not in ("id", "parent", "mirror")}
            try:
                s = fill(s, ctx)
            except ValueError as e:
                raise ValueError(f"rows[{i}], template[{k}]: {e}") from e
            if name in ids:
                s["id"] = ids[name]
            if s.get("fit_to"):  # a rect fitted around template elements of the same row
                targets = s["fit_to"] if isinstance(s["fit_to"], list) else [s["fit_to"]]
                s["fit_to"] = [ids.get(t, t) for t in targets]
            parent = spec.get("parent")
            if parent:
                if parent not in ids:
                    raise ValueError(f"template[{k}]: parent {parent!r} must be the id of another template element")
                if names.index(parent) >= k:
                    raise ValueError(f"template[{k}]: parent {parent!r} must come before its children")
                s["parent"] = ids[parent]
            default_mode = "block" if spec["type"] in ("text", "group") else "reflect"
            stamped.append((name, s, "none" if parent else spec.get("mirror", default_mode)))
        out.append(stamped)
    return out


def offset(i: int, step: list[float], columns: int | None) -> tuple[float, float]:
    """Row i's offset: along `step` for a single run, or a grid of `columns` (step = [dx, dy])."""
    if columns:
        return (i % columns) * step[0], (i // columns) * step[1]
    return i * step[0], i * step[1]
