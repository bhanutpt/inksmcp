"""CI: prove Inkscape works before the tests run, and say why when it doesn't (standard output only).

One shell round trip: version, open a small SVG from the temp folder, query it. Each step's raw output
goes out as a GitHub `::notice` annotation, visible without signing in (job logs are not).

  uv run python scripts/ci_inkscape_check.py
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

from inksmcp.inkscape import InkscapeShell, find_inkscape, inkscape_version


def note(title: str, text: str, level: str = "notice") -> None:
    body = text.replace("%", "%25").replace("\r", "").replace("\n", "%0A")[:3000]
    print(f"::{level} title={title}::{body}")


def main() -> int:
    exe = find_inkscape()
    note("inkscape", f"{exe}\n{inkscape_version(exe)}\ntemp: {tempfile.gettempdir()}")
    folder = Path(tempfile.mkdtemp(prefix="inksmcp-check-"))
    svg = folder / "check.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">'
                   '<rect id="r" x="10" y="20" width="30" height="40"/></svg>', encoding="utf-8")
    ok = False
    with InkscapeShell(exe) as sh:
        for cmd in ("file-close", f"file-open:{svg}", "query-all", "file-close"):
            t = time.perf_counter()
            res = sh.run(cmd, check=False)
            ms = (time.perf_counter() - t) * 1000
            note(f"shell {cmd[:40]}", f"{ms:.0f} ms\nstdout: {res.output!r}\nstderr: {res.messages!r}")
            if cmd == "query-all":
                ok = any(line.startswith("r,") for line in res.output.splitlines())
    if not ok:
        note("inkscape check", "Inkscape did not report the rect after file-open: documents don't load.", "error")
        return 1
    note("inkscape check", "file-open + query-all work")
    return 0


if __name__ == "__main__":
    sys.exit(main())
