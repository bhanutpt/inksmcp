"""End-to-end through the MCP protocol with an in-process client."""
import json

import pytest
from mcp import Client

from inksmcp import server


@pytest.fixture
def fresh_session(engine, monkeypatch):
    s = server.Session()
    s._engine = engine
    monkeypatch.setattr(server, "session", s)
    return s


async def call(client, name, **args):
    r = await client.call_tool(name, args)
    return r


def text(r):
    return json.loads(r.content[0].text)


@pytest.mark.anyio
async def test_tools_are_listed():
    async with Client(server.mcp) as c:
        names = {t.name for t in (await c.list_tools()).tools}
    assert {"document_create", "add_elements", "inspect", "render_preview", "export", "path_operation"} <= names


@pytest.mark.anyio
async def test_poster_workflow(fresh_session, tmp_path):
    async with Client(server.mcp) as c:
        r = await call(c, "document_create", width=200, height=100, unit="mm", background="#fdf6e3")
        assert text(r)["doc_id"] == "doc1"

        r = await call(c, "add_elements", elements=[
            {"type": "rect", "id": "card", "x": 20, "y": 20, "width": 80, "height": 60, "rx": 5,
             "fill": "#268bd2", "layer": "Shapes"},
            {"type": "circle", "id": "dot", "cx": 150, "cy": 50, "r": 25, "fill": "#dc322f", "layer": "Shapes"},
            {"type": "text", "id": "title", "x": 60, "y": 55, "text": "inksmcp", "font_size": 10,
             "text_anchor": "middle", "fill": "#ffffff", "layer": "Text"},
        ], preview=True)
        assert not r.is_error, r.content
        assert text(r)["ids"] == ["card", "dot", "title"]
        assert r.content[1].type == "image" and r.content[1].mime_type == "image/png"

        r = await call(c, "inspect")
        outline = text(r)["outline"]
        layers = {n["label"]: n for n in outline if n["type"] == "layer"}
        assert set(layers) == {"Shapes", "Text"}
        title = layers["Text"]["children"][0]
        assert title["id"] == "title" and title["text"] == "inksmcp"
        x, y, w, h = title["bbox"]
        assert abs((x + w / 2) - 60) < 1  # text-anchor middle centred on x=60

        r = await call(c, "path_operation", operation="union", ids=["card", "dot"])
        assert text(r)["removed"] == ["dot"]

        r = await call(c, "export", path=str(tmp_path / "poster.pdf"))
        assert text(r)["bytes"] > 0
        r = await call(c, "document_save", path=str(tmp_path / "poster.svg"))
        assert (tmp_path / "poster.svg").exists()

        r = await call(c, "render_preview", max_size=300)
        assert r.content[0].type == "image"


@pytest.mark.anyio
async def test_errors_are_reported_to_the_agent(fresh_session):
    async with Client(server.mcp) as c:
        r = await call(c, "inspect")
        assert r.is_error and "document_create" in r.content[0].text
        await call(c, "document_create", width=10, height=10)
        r = await call(c, "add_elements", elements=[{"type": "rect"}, {"type": "blob"}])
        assert r.is_error and "elements[1]" in r.content[0].text
        r = await call(c, "inspect", bbox=False)
        assert text(r)["outline"] == []  # all-or-nothing: first rect rolled back
        r = await call(c, "run_actions", actions=["quit"])
        assert r.is_error and "not allowed" in r.content[0].text
