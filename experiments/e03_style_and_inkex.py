"""E03: Does path-union keep style="..." (vs presentation attrs)? Is inkex usable?

Run: python experiments/e03_style_and_inkex.py
"""
import subprocess
from pathlib import Path

INK = r"C:\Program Files\Inkscape\bin\inkscape.com"
OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" viewBox="0 0 200 100">
  <rect id="r1" x="10" y="10" width="80" height="80" style="fill:#3366ff;stroke:#000;stroke-width:2"/>
  <circle id="c1" cx="90" cy="50" r="40" style="fill:#ff6633"/>
</svg>"""
src = OUT / "e03.svg"
src.write_text(SVG, encoding="utf-8")
dst = OUT / "e03_union.svg"
p = subprocess.run([INK, str(src), f"--actions=select-by-id:r1,c1;path-union;export-filename:{dst};export-plain-svg;export-do"],
                   capture_output=True, text=True)
print("stderr:", p.stderr.strip())
print([l.strip() for l in dst.read_text().splitlines() if "style" in l or "<path" in l or "id=" in l])

# inkex via Inkscape's bundled python
bundled = r"C:\Program Files\Inkscape\bin\python.exe"
code = "import inkex, sys; print(sys.version.split()[0], inkex.__version__ if hasattr(inkex,'__version__') else 'n/a', inkex.__file__)"
p = subprocess.run([bundled, "-c", code], capture_output=True, text=True)
print("bundled python:", p.stdout.strip(), p.stderr.strip()[-300:])
