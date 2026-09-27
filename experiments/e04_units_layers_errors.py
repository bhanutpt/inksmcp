"""E04: query units with mm documents, layer survival through shell export, missing-file errors.

Run: python experiments/e04_units_layers_errors.py
"""
import subprocess
from pathlib import Path

INK = r"C:\Program Files\Inkscape\bin\inkscape.com"
OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

SVG = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
  width="100mm" height="50mm" viewBox="0 0 100 50">
  <g id="layer1" inkscape:groupmode="layer" inkscape:label="Background">
    <rect id="r1" x="10" y="10" width="20" height="20" style="fill:#3366ff"/>
  </g>
  <g id="layer2" inkscape:groupmode="layer" inkscape:label="Top">
    <rect id="r2" x="50" y="10" width="20" height="20" style="fill:#ff6633" transform="rotate(45 60 20)"/>
  </g>
</svg>"""
src = OUT / "e04.svg"
src.write_text(SVG, encoding="utf-8")
out = OUT / "e04_rt.svg"
script = "\n".join([
    f"file-open:{src}",
    "query-all",
    "select-by-id:r1;object-to-path",
    f"export-filename:{out}",
    "export-type:svg",
    "export-do",
    "file-close",
    f"file-open:{OUT / 'does_not_exist.svg'}",
    "query-all",
    "quit",
])
p = subprocess.run([INK, "--shell"], input=script, capture_output=True, text=True)
print("STDOUT:\n", p.stdout)
print("STDERR:\n", p.stderr)
print("ROUNDTRIP layers kept:", "inkscape:groupmode=\"layer\"" in out.read_text(), "| r1 is path:", '<path' in out.read_text())
print([l.strip() for l in out.read_text().splitlines() if "width=" in l or "viewBox" in l or "sodipodi:namedview" in l][:5])
