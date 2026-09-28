"""Every recipe in docs/recipes.md runs: each ```json block starting with `// tool_name` is one call.
A recipe is the calls under one `## ` heading; document_create starts a fresh document."""
import json
import re
from pathlib import Path

import pytest
from mcp import Client

from inksmcp import server

RECIPES = Path(__file__).resolve().parents[1] / "docs" / "recipes.md"


def recipes() -> list[tuple[str, list[tuple[str, dict]]]]:
    out = []
    for section in re.split(r"^## ", RECIPES.read_text(encoding="utf-8"), flags=re.M)[1:]:
        title = section.splitlines()[0]
        calls = [(m.group(1), json.loads(m.group(2)))
                 for m in re.finditer(r"```json\n// (\w+)\n(.*?)```", section, re.S)]
        if calls:
            out.append((title, calls))
    return out


def test_recipes_are_found():
    assert len(recipes()) >= 6


@pytest.fixture
def fresh_session(engine, monkeypatch):
    s = server.Session()
    s._engine = engine
    monkeypatch.setattr(server, "session", s)
    return s


@pytest.mark.anyio
@pytest.mark.parametrize("title,calls", recipes(), ids=[t for t, _ in recipes()])
async def test_recipe_runs(fresh_session, tmp_path, title, calls):
    async with Client(server.mcp) as c:
        for tool, args in calls:
            if "path" in args and tool == "export":
                args = {**args, "path": str(tmp_path / args["path"])}
            r = await c.call_tool(tool, args)
            assert not r.is_error, f"{title}: {tool} failed: {r.content[0].text}"
            if tool == "export":
                assert Path(args["path"]).stat().st_size > 0
