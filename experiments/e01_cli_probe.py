"""E01: Probe Inkscape CLI behaviour — export, query, actions, timings.

Run: uv run python experiments/e01_cli_probe.py
Findings are recorded in docs/05-inkscape-notes.md.
"""
import subprocess
import time
from pathlib import Path

INK = r"C:\Program Files\Inkscape\bin\inkscape.com"
OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" viewBox="0 0 200 100">
  <rect id="r1" x="10" y="10" width="80" height="80" fill="#3366ff"/>
  <circle id="c1" cx="90" cy="50" r="40" fill="#ff6633"/>
  <text id="t1" x="120" y="55" font-size="20">Hi</text>
</svg>"""


def run(*args, stdin=None):
    t = time.perf_counter()
    p = subprocess.run([INK, *args], capture_output=True, text=True, input=stdin)
    dt = (time.perf_counter() - t) * 1000
    print(f"\n$ inkscape {' '.join(args)}  [{dt:.0f} ms, rc={p.returncode}]")
    if p.stdout.strip():
        print("stdout:", p.stdout.strip()[:800])
    if p.stderr.strip():
        print("stderr:", p.stderr.strip()[:800])
    return p


src = OUT / "e01.svg"
src.write_text(SVG, encoding="utf-8")

# 1. export png
run(str(src), "--export-type=png", f"--export-filename={OUT / 'e01.png'}")
# 2. export pdf
run(str(src), "--export-type=pdf", f"--export-filename={OUT / 'e01.pdf'}")
# 3. query all bounding boxes
run(str(src), "--query-all")
# 4. action chain: select two shapes, union, save as new file
run(str(src), "--actions=select-by-id:r1,c1;path-union;export-filename:"
    + str(OUT / "e01_union.svg") + ";export-plain-svg;export-do")
print("union result:", (OUT / "e01_union.svg").read_text()[:600] if (OUT / "e01_union.svg").exists() else "MISSING")
# 5. text to path
run(str(src), "--actions=select-by-id:t1;object-to-path;export-filename:"
    + str(OUT / "e01_textpath.svg") + ";export-do")
# 6. bad id — how are errors reported?
run(str(src), "--actions=select-by-id:nope;path-union")
# 7. bad action
run(str(src), "--actions=not-an-action")
# 8. export from stdin
run("--pipe", "--export-type=png", f"--export-filename={OUT / 'e01_pipe.png'}", stdin=SVG)
