"""Prepare a release: set the version everywhere and turn CHANGELOG's Unreleased entries into its section.

  uv run python scripts/bump_version.py 0.3.1
  uv run python scripts/bump_version.py 0.3.1 --date 2026-10-05

Updates src/inksmcp/__init__.py, server.json (server and package versions) and CHANGELOG.md, then
regenerates docs/tools.md. Review the diff, run the tests, commit, then tag vX.Y.Z and push the tag.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))  # keep LF endings on Windows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("version")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    a = ap.parse_args()
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[ab]\d+|rc\d+)?", a.version):
        raise SystemExit(f"Not a version: {a.version}")

    init = ROOT / "src" / "inksmcp" / "__init__.py"
    write(init, re.sub(r'__version__ = "[^"]+"', f'__version__ = "{a.version}"', init.read_text(encoding="utf-8")))

    sj = ROOT / "server.json"
    server = json.loads(sj.read_text(encoding="utf-8"))
    server["version"] = a.version
    for p in server["packages"]:
        p["version"] = a.version
    write(sj, json.dumps(server, indent=2, ensure_ascii=False) + "\n")

    cl = ROOT / "CHANGELOG.md"
    text = cl.read_text(encoding="utf-8")
    if f"## {a.version} " in text:
        print(f"CHANGELOG.md already has a {a.version} section; left as it is.")
    else:
        m = re.search(r"^## Unreleased\n(.*?)(?=^## )", text, re.M | re.S)
        if not m or not m.group(1).strip():
            raise SystemExit("CHANGELOG.md: nothing under '## Unreleased' to release.")
        text = text[:m.start()] + f"## Unreleased\n\n## {a.version} — {a.date}\n\n{m.group(1).strip()}\n\n" + text[m.end():]
        write(cl, text)

    subprocess.run([sys.executable, str(ROOT / "scripts" / "gen_tools_doc.py")], check=True)
    print(f"Version {a.version} set. Next: uv run pytest, commit, git tag v{a.version}, git push origin v{a.version}")


if __name__ == "__main__":
    main()
