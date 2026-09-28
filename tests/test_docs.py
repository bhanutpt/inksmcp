"""Release hygiene: the generated tool reference and the version numbers stay in step."""
import asyncio
import importlib.util
import json
from pathlib import Path

from inksmcp import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_tool_reference_is_current():
    spec = importlib.util.spec_from_file_location("gen_tools_doc", ROOT / "scripts" / "gen_tools_doc.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    current = (ROOT / "docs" / "tools.md").read_text(encoding="utf-8")
    assert asyncio.run(gen.render()) == current, "docs/tools.md is stale: run uv run python scripts/gen_tools_doc.py"


def test_versions_agree():
    server = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    assert server["version"] == __version__
    assert all(p["version"] == __version__ for p in server["packages"])
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## {__version__} " in changelog, f"CHANGELOG.md has no section for {__version__}"


def test_readme_names_the_registry_server():
    server = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    assert f"mcp-name: {server['name']} -->" in (ROOT / "README.md").read_text(encoding="utf-8")
