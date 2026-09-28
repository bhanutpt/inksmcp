"""Turn pytest's JUnit XML into GitHub annotations and a job summary (CI only, standard library).

Job logs of a public repository need a signed-in GitHub account; annotations and summaries don't, and
they show on pull requests next to the code.

  python scripts/ci_annotate.py junit.xml
"""
from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET


def esc(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "").replace("\n", "%0A")


def main(path: str) -> None:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as e:
        print(f"::error title=pytest::No test report ({e}); the run failed before or during collection.")
        return
    failed = []
    for case in root.iter("testcase"):
        for kind in ("failure", "error"):
            el = case.find(kind)
            if el is not None:
                file = case.get("file") or case.get("classname", "").replace(".", "/") + ".py"
                name = case.get("name", "?")
                lines = (el.text or "").strip().splitlines()
                detail = "\n".join(lines[-25:])
                failed.append((file, case.get("line"), name, el.get("message", "").strip(), detail, kind))
    totals = {k: sum(int(s.get(k, 0)) for s in root.iter("testsuite")) for k in ("tests", "failures", "errors", "skipped")}
    for file, line, name, message, detail, kind in failed:
        where = f"file={file}" + (f",line={int(line) + 1}" if line and line.isdigit() else "")
        print(f"::error {where},title={kind}: {name}::{esc(message[:300] + chr(10) + detail[-2500:])}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"### pytest: {totals['tests']} tests, {totals['failures']} failed, {totals['errors']} errors, "
                    f"{totals['skipped']} skipped\n\n")
            for file, _, name, message, detail, kind in failed:
                f.write(f"<details><summary><code>{name}</code> ({file}): {message[:150]}</summary>\n\n"
                        f"```\n{detail[-4000:]}\n```\n</details>\n\n")
    print(f"{len(failed)} failing tests annotated")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "junit.xml")
