"""Release helpers for .github/workflows/release.yml (standard library only).

  python3 scripts/release_notes.py 0.3.0           print that version's CHANGELOG.md section
  python3 scripts/release_notes.py --check 0.3.0   fail unless the package, server.json and CHANGELOG agree
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def package_version() -> str:
    text = (ROOT / "src" / "inksmcp" / "__init__.py").read_text(encoding="utf-8")
    return re.search(r'__version__ = "([^"]+)"', text).group(1)


def section(version: str) -> str:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(rf"^## {re.escape(version)} .*?$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        raise SystemExit(f"CHANGELOG.md has no '## {version} ...' section.")
    return m.group(1).strip() + "\n"


def check(version: str) -> None:
    server = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    found = {"tag": version, "src/inksmcp/__init__.py": package_version(), "server.json": server["version"],
             **{f"server.json packages[{i}]": p["version"] for i, p in enumerate(server["packages"])}}
    if len(set(found.values())) != 1:
        raise SystemExit("Versions disagree: " + ", ".join(f"{k}={v}" for k, v in found.items()))
    section(version)
    print(f"version {version}: package, server.json and CHANGELOG agree")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--check"] and len(args) == 2:
        check(args[1])
    elif len(args) == 1:
        sys.stdout.buffer.write(section(args[0]).encode("utf-8"))
    else:
        raise SystemExit(__doc__)
