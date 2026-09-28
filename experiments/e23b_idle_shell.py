"""E23b: Does an idle shell die? The comic crash (field report 5) was the first command after the
server's shell had sat idle for ~28 minutes with no document open (the state `_close` leaves it in).

Run: uv run python experiments/e23b_idle_shell.py [minutes]
"""
import sys
import time

from inksmcp.document import Document
from inksmcp.engine import Engine
from inksmcp.inkscape import InkscapeError

minutes = float(sys.argv[1]) if len(sys.argv) > 1 else 15
eng = Engine()
doc = Document.create(100, 100, "mm")
doc.add({"type": "rect", "id": "r", "x": 10, "y": 10, "width": 20, "height": 20})
print("before idle:", eng.bboxes(doc)["r"], "pid", eng.shell._proc.pid, flush=True)
t0 = time.time()
while time.time() - t0 < minutes * 60:
    time.sleep(30)
    code = eng.shell._proc.poll()
    if code is not None:
        print(f"died while idle after {time.time() - t0:.0f}s, exit code {code}", flush=True)
        break
print(f"idle {time.time() - t0:.0f}s, alive={eng.shell.alive}", flush=True)
try:
    print("after idle:", eng.bboxes(doc)["r"], "pid", eng.shell._proc.pid, "restarts", eng.shell.restarts)
except InkscapeError as e:
    print("after idle: FAILED", e)
eng.close()
