"""E17: From field report 2026-09-27-heat-pump-poster.

A. Multi-line text: how does Inkscape lay out sodipodi:role="line" tspans with dy (our current output)
   vs. role=line + line-height style, vs. plain tspans with dy, vs. explicit y per tspan?
B. Arrow stub past the tip: marker refX at the tip (10) vs 8 vs 7 — zoomed renders.
C. Does Inkscape 1.4 honour inkscape:connection-start-point (connect to a side/point)?
D. Does inline-size (SVG2 wrapping) render in PNG export?

Run: uv run python experiments/e17_text_lines_arrows.py
"""
from pathlib import Path

from inksmcp.document import Document
from inksmcp.engine import Engine

OUT = Path(__file__).parent / "out" / "e17"
OUT.mkdir(parents=True, exist_ok=True)
eng = Engine()
NS = 'xmlns="http://www.w3.org/2000/svg" xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd" ' \
     'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"'

print("A. line baselines (font 10, want spacing 12.5 = 1.25em)")
variants = {
    "role_dy": '<text id="t" x="10" y="20" style="font-size:10px"><tspan sodipodi:role="line" x="10">Hxy</tspan>'
               '<tspan sodipodi:role="line" x="10" dy="1.25em">Hxy</tspan><tspan sodipodi:role="line" x="10" dy="1.25em">Hxy</tspan></text>',
    "role_lh": '<text id="t" x="10" y="20" style="font-size:10px;line-height:1.25"><tspan sodipodi:role="line" x="10">Hxy</tspan>'
               '<tspan sodipodi:role="line" x="10">Hxy</tspan><tspan sodipodi:role="line" x="10">Hxy</tspan></text>',
    "plain_dy": '<text id="t" x="10" y="20" style="font-size:10px"><tspan x="10">Hxy</tspan>'
                '<tspan x="10" dy="1.25em">Hxy</tspan><tspan x="10" dy="1.25em">Hxy</tspan></text>',
    "plain_y": '<text id="t" x="10" y="20" style="font-size:10px"><tspan x="10" y="20">Hxy</tspan>'
               '<tspan x="10" y="32.5">Hxy</tspan><tspan x="10" y="45">Hxy</tspan></text>',
    "role_lh_y": '<text id="t" x="10" y="20" style="font-size:10px;line-height:1.25"><tspan sodipodi:role="line" x="10" y="20">Hxy</tspan>'
                 '<tspan sodipodi:role="line" x="10" y="32.5">Hxy</tspan><tspan sodipodi:role="line" x="10" y="45">Hxy</tspan></text>',
}
for name, body in variants.items():
    doc = Document.from_bytes(f'<svg {NS} width="100" height="100" viewBox="0 0 100 100">{body}</svg>'.encode())
    for i, sp in enumerate(doc.get("t")):
        sp.set("id", f"s{i}")
    b = eng.bboxes(doc)
    bottoms = [round(b[f"s{i}"][1] + b[f"s{i}"][3], 2) for i in range(3)]
    eng.run_actions(doc, [])  # what does Inkscape write back?
    written = [(sp.get("y"), sp.get("dy")) for sp in doc.get("t")]
    print(f"   {name:10s} glyph bottoms={bottoms} written(y,dy)={written}")
    eng.export(doc, OUT / f"A_{name}.png", width=200, background="#fff")

print("B. arrow tip stub (see B_*.png)")
for ref in (10, 8, 7):
    doc = Document.from_bytes(f'''<svg {NS} width="40" height="20" viewBox="0 0 40 20">
      <defs><marker id="m" viewBox="0 0 10 10" refX="{ref}" refY="5" markerWidth="5" markerHeight="5"
        orient="auto-start-reverse" markerUnits="strokeWidth"><path d="M 0,0 L 10,5 L 0,10 z" style="fill:#c00"/></marker></defs>
      <rect id="box" x="30" y="2" width="8" height="16" style="fill:#eee;stroke:#333;stroke-width:0.3"/>
      <path id="p" d="M 2,10 H 30" style="fill:none;stroke:#c00;stroke-width:1.2;marker-end:url(#m)"/></svg>'''.encode())
    eng.export(doc, OUT / f"B_ref{ref}.png", region=(22, 5, 10, 10), width=400, background="#fff")
    print(f"   refX={ref}: p bbox={tuple(round(v, 2) for v in eng.bboxes(doc)['p'])}")

print("C. connection-start-point")
doc = Document.from_bytes(f'''<svg {NS} width="100" height="60" viewBox="0 0 100 60">
  <rect id="a" x="10" y="10" width="20" height="20"/><rect id="b" x="70" y="30" width="20" height="20"/>
  <path id="k" d="M 0,0" style="fill:none;stroke:#000" inkscape:connector-type="orthogonal"
     inkscape:connection-start="#a" inkscape:connection-start-point="d4"
     inkscape:connection-end="#b" inkscape:connection-end-point="d4"/></svg>'''.encode())
eng.run_actions(doc, [])
print("   d =", doc.get("k").get("d"), {k.split('}')[1]: v for k, v in doc.get("k").attrib.items() if "point" in k})

print("D. inline-size wrapping")
doc = Document.from_bytes(f'''<svg {NS} width="100" height="60" viewBox="0 0 100 60">
  <text id="w" x="5" y="10" style="font-size:5px;inline-size:40px">The quick brown fox jumps over the lazy dog again and again</text></svg>'''.encode())
print("   bbox (w <= 40 means wrapped):", tuple(round(v, 2) for v in eng.bboxes(doc)["w"]))
eng.export(doc, OUT / "D_inline_size.png", width=300, background="#fff")
eng.close()
