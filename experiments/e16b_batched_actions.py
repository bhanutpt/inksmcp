"""E16b: grid took 11 s because translate sends 3 shell commands per element. Is one long
`;`-joined line safe (length limit?) and faster? Does a multi-id selection translate every item?

Run: uv run python experiments/e16b_batched_actions.py
"""
import time

from inksmcp.document import Document
from inksmcp.engine import Engine

eng = Engine()
N = 300


def make():
    doc = Document.create(1000, 1000)
    for i in range(N):
        doc.add({"type": "rect", "id": f"r{i}", "x": i * 3, "y": 0, "width": 2, "height": 2})
    return doc


for mode in ("per-command", "one-line", "one-selection"):
    doc = make()
    src = eng._open(doc)
    t = time.perf_counter()
    if mode == "per-command":
        for i in range(N):
            eng.shell.run(f"select-clear;select-by-id:r{i};transform-translate:0,10")
    elif mode == "one-line":
        line = ";".join(f"select-clear;select-by-id:r{i};transform-translate:0,10" for i in range(N))
        print(f"   line length: {len(line)} chars")
        eng.shell.run(line)
    else:
        eng.shell.run("select-clear;select-by-id:" + ",".join(f"r{i}" for i in range(N)) + ";transform-translate:0,10")
    dt = (time.perf_counter() - t) * 1000
    out = eng.shell.run("query-all").output
    eng._close(src)
    ys = {line.split(",")[2] for line in out.splitlines() if line.startswith("r")}
    print(f"{mode:14s} {dt:7.0f} ms  distinct y after move: {ys}")
eng.close()
