"""E23: Can we reproduce the intermittent shell crash from field report 5 (comic)?
  "Inkscape shell exited unexpectedly: InkscapeApplication::close_document: No document!
   Magick: quitting due to signal 51 (SIGTERM) ..."
Questions:
  A. Does `file-close` with no document open print "No document!" (i.e. is that line just noise)?
  B. Does a long loop of the server's real cycle (file-close, file-open, query-all, export svg/png,
     file-close) ever kill the shell? What exit code and stderr does it leave?
  C. After a death, does the next command start a fresh shell and succeed?

Run: uv run python experiments/e23_shell_crash.py [iterations]
"""
import sys
import time

from inksmcp.document import Document
from inksmcp.engine import Engine
from inksmcp.inkscape import InkscapeError, InkscapeShell

sh = InkscapeShell()
sh.start()
r = sh.run("file-close", check=False)
print("A file-close with no document -> messages:", r.messages)
r = sh.run("file-close", check=False)
print("  again ->", r.messages)
sh.close()

N = int(sys.argv[1]) if len(sys.argv) > 1 else 150
eng = Engine()
doc = Document.create(210, 297, "mm")
for k in range(40):
    doc.add({"type": "rect", "id": f"r{k}", "x": 5 + 4 * k, "y": 10, "width": 20, "height": 10, "fill": "#c00",
             "layer": "Panels"})
    doc.add({"type": "text", "id": f"t{k}", "x": 5 + 4 * k, "y": 40 + k, "text": f"Label number {k} wraps",
             "font_size": 3, "width": 20, "font_family": "Comic Sans MS"})
    doc.add({"type": "rect", "id": f"f{k}", "fit_to": [f"t{k}"], "fit_padding": 1, "fill": "#fff", "stroke": "#000"})
deaths, t0 = [], time.time()
for i in range(N):
    try:
        eng.wrap_texts(doc, [f"t{k}" for k in range(40)])
        eng.anchor_texts(doc, {f"t{k}": ("middle", 40 + k) for k in range(0, 40, 5)})
        eng.fit_rects(doc, {f"t{k}" for k in range(40)})
        if i % 5 == 0:
            eng.render_png(doc, max_size=400)
    except InkscapeError as e:
        code = eng.shell._proc.poll() if eng.shell._proc else None
        deaths.append((i, code, str(e)[:300]))
        print(f"B iteration {i}: {e!s:.300} (exit code {code})")
    if i % 25 == 0:
        print(f"  {i}/{N} {time.time() - t0:.0f}s deaths={len(deaths)}", flush=True)
print(f"B {N} iterations, {len(deaths)} deaths, {time.time() - t0:.0f}s")
if deaths:
    print("C next call after a death:", len(eng.bboxes(doc)), "boxes")
eng.close()
