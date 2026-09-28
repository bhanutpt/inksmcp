"""Write docs/tools.md from the server's own tool list, so the reference never drifts from what agents see.

Run: uv run python scripts/gen_tools_doc.py        (tests/test_docs.py fails when the file is stale)
"""
from __future__ import annotations

import asyncio
import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inksmcp.server import mcp  # noqa: E402

TARGET = ROOT / "docs" / "tools.md"
GROUPS = [
    ("Documents", ["inkscape_info", "document_create", "document_open", "document_save", "inspect"]),
    ("Elements", ["add_elements", "update_elements", "delete_elements", "import_file", "repeat"]),
    ("Arrangement", ["align", "layout", "split", "connect", "z_order", "move_to_layer", "page_fit", "page_resize"]),
    ("Charts and paper", ["grid", "plot"]),
    ("Paths and raw actions", ["path_operation", "run_actions"]),
    ("Output", ["render_preview", "export"]),
]


def type_of(schema: dict, defs: dict) -> str:
    if "$ref" in schema:
        return schema["$ref"].rsplit("/", 1)[-1]
    if "anyOf" in schema:
        kinds = [type_of(s, defs) for s in schema["anyOf"] if s.get("type") != "null"]
        return " \\| ".join(kinds) or "null"
    if "enum" in schema:
        return " \\| ".join(json.dumps(v) for v in schema["enum"])
    t = schema.get("type", "any")
    if t == "array":
        return f"list[{type_of(schema.get('items', {}), defs)}]"
    return {"object": "object", "integer": "int", "number": "number", "string": "string", "boolean": "bool"}.get(t, t)


def cell(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def params_table(schema: dict) -> list[str]:
    props = schema.get("properties") or {}
    if not props:
        return ["No parameters."]
    required = set(schema.get("required") or [])
    defs = schema.get("$defs") or {}
    rows = ["| Parameter | Type | Default | Description |", "|---|---|---|---|"]
    for name, p in props.items():
        default = "required" if name in required else json.dumps(p.get("default")) if "default" in p else ""
        rows.append(f"| `{name}` | {type_of(p, defs)} | {cell(default)} | {cell(p.get('description', ''))} |")
    for dname, d in defs.items():  # nested models (e.g. connect's Connection)
        rows += ["", f"`{dname}` fields:", "", "| Field | Type | Default | Description |", "|---|---|---|---|"]
        dreq = set(d.get("required") or [])
        for name, p in (d.get("properties") or {}).items():
            default = "required" if name in dreq else json.dumps(p.get("default")) if "default" in p else ""
            rows.append(f"| `{name}` | {type_of(p, defs)} | {cell(default)} | {cell(p.get('description', ''))} |")
    return rows


async def render() -> str:
    tools = {t.name: t for t in await mcp.list_tools()}
    listed = [n for _, names in GROUPS for n in names]
    missing = sorted(set(tools) - set(listed))
    if missing:
        raise SystemExit(f"Add these tools to GROUPS in {Path(__file__).name}: {missing}")
    out = ["# Tool reference", "",
           f"inksmcp exposes {len(tools)} tools. This page is generated from the server itself "
           "(`scripts/gen_tools_doc.py`), so it matches what an agent sees. For how the tools combine, "
           "see [recipes](recipes.md).", "",
           "All coordinates are in the document's user units (the unit given at creation; origin top-left, "
           "y down). Tools act on the current document unless `doc_id` is given. Every tool is all-or-nothing: "
           "on an error nothing is changed.", ""]
    for title, names in GROUPS:
        out.append(f"- **{title}**: " + ", ".join(f"[`{n}`](#{n})" for n in names))
    for title, names in GROUPS:
        out += ["", f"## {title}"]
        for n in names:
            t = tools[n]
            out += ["", f"### {n}", "", inspect.cleandoc(t.description or ""), ""]
            out += params_table(t.input_schema)
    return "\n".join(out) + "\n"


def main() -> None:
    text = asyncio.run(render())
    TARGET.write_bytes(text.encode("utf-8"))
    print(f"wrote {TARGET.relative_to(ROOT)} ({len(text):,} chars)")


if __name__ == "__main__":
    main()
